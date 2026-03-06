import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.schema.chat import ChatHistoryResponse, ChatMessageResponse, ChatSendRequest, ChatSendResponse
from api.schema.survey import (
    Survey1Request, Survey1Response,
    Survey3Request, Survey3Response,
)
from api.services.llm import generate_chat_reply

load_dotenv()

app = FastAPI(
    title="Persuasive AI Study API",
    description="API for collecting and storing survey responses for the Persuasive AI study",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "persuasive_ai_study")

_client = None
_db = None
_survey1_collection = None

# Process-local guard for one active generation per participant+condition in local dev.
_inflight_sessions: set[tuple[str, str]] = set()
_inflight_lock = asyncio.Lock()


def get_database():
    """Get database connection, reusing existing connection for serverless."""
    global _client, _db, _survey1_collection

    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URL,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
        )
        _db = _client[DATABASE_NAME]
        _survey1_collection = _db["survey1_responses"]

    return _client, _db, _survey1_collection


async def _acquire_inflight(participant_id: str, condition_key: str) -> bool:
    # Atomically mark a session as busy so concurrent sends return 409.
    key = (participant_id, condition_key)
    async with _inflight_lock:
        if key in _inflight_sessions:
            return False
        _inflight_sessions.add(key)
        return True


async def _release_inflight(participant_id: str, condition_key: str) -> None:
    # Always clear busy flag after request completion/error.
    key = (participant_id, condition_key)
    async with _inflight_lock:
        _inflight_sessions.discard(key)


def _to_chat_session_response(session) -> ChatSessionResponse:
    return ChatSessionResponse(
        participant_id=session.participant_id,
        condition_key=session.condition_key,
        condition_label=session.condition_label,
        topic=session.topic,
        statement=session.statement,
        messages=session.messages,
    )


@app.get("/", response_class=FileResponse)
async def home_page():
    """Serve the demo frontend. It handles setup mode vs chat mode based on query params."""
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(frontend_path)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        client, _, _ = get_database()
        await client.admin.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(UTC),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


@app.post(
    "/api/v1/survey1",
    response_model=Survey1Response,
    status_code=status.HTTP_201_CREATED,
)
async def submit_survey1(survey_data: Survey1Request):
    """Submit Survey 1 responses from Qualtrics and store them in MongoDB."""
    try:
        client, db, survey1_collection = get_database()
        
        block_doc = None
        if survey_data.pre_block_id is not None:
            br = survey_data.block_responses
            block_doc = {
                "block_id": survey_data.pre_block_id,
                "topic": survey_data.pre_topic,
                "personalization": survey_data.pre_personalization,
                "is_control": survey_data.pre_is_control,
            }
            if br:
                block_doc["opinion"] = br.opinion
                block_doc["opinion_reason"] = br.opinion_reason
                block_doc["statements"] = [
                    {"statement_id": s.statement_id, "response": s.response}
                    for s in (br.statements or [])
                ]
                block_doc["feeling_strength"] = br.feeling_strength
                block_doc["topic_importance"] = br.topic_importance

        document = {
            "participant_id": survey_data.participant_id,
            "prolific_id": survey_data.prolific_id,
            "qualtrics_response_id": survey_data.qualtrics_response_id,
            "topic_condition": survey_data.topic_condition,
            "topic_usage": survey_data.topic_usage,
            "topic_behavior": survey_data.topic_behavior,
            "pre_block": block_doc,
            "demographics": survey_data.demographics.model_dump() if survey_data.demographics else None,
            "survey_comment": survey_data.survey_comment,
            "survey_completion_time": survey_data.survey_completion_time or datetime.utcnow(),
            "ip_address": survey_data.ip_address,
            "user_agent": survey_data.user_agent,
            "created_at": datetime.now(UTC),
            "survey_type": "survey1_baseline",
            "week": 0,
        }

        result = await survey1_collection.insert_one(document)

        return Survey1Response(
            success=True,
            message="Survey 1 response stored successfully",
            participant_id=survey_data.participant_id,
            survey_id=str(result.inserted_id),
            timestamp=datetime.now(UTC),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store survey response: {str(e)}",
        )


@app.get("/api/v1/chat/conditions", response_model=ConditionsResponse)
async def get_conditions():
    return ConditionsResponse(conditions=condition_metadata())


@app.post("/api/v1/chat/initialize", response_model=ChatSessionResponse)
async def initialize_chat(payload: ChatInitializeRequest):
    try:
        session = await initialize_chat_session(
            participant_id=payload.participant_id,
            condition_key=payload.condition_key,
            user_answer=payload.user_answer,
            argument=payload.argument,
        )
        return _to_chat_session_response(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize chat: {str(e)}",
        )


@app.get("/api/v1/chat/sessions/{participant_id}", response_model=ChatSessionsResponse)
async def get_chat_sessions(participant_id: str):
    sessions = await list_participant_sessions(participant_id)
    summaries = [
        {
            "participant_id": session.participant_id,
            "condition_key": session.condition_key,
            "condition_label": session.condition_label,
            "topic": session.topic,
            "statement": session.statement,
            "updated_at": session.updated_at,
        }
        for session in sessions
    ]
    return ChatSessionsResponse(participant_id=participant_id, sessions=summaries)


@app.get(
    "/api/v1/chat/history/{participant_id}/{condition_key}",
    response_model=ChatSessionResponse,
)
async def get_chat_history(participant_id: str, condition_key: str):
    try:
        session = await get_chat_session(participant_id, condition_key)
        return _to_chat_session_response(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}",
        )


@app.post("/api/v1/chat/send", response_model=ChatSendResponse)
async def send_chat_message(payload: ChatSendRequest):
    acquired = await _acquire_inflight(payload.participant_id, payload.condition_key)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A response is already being generated for this participant and condition",
        )

    try:
        session = await append_and_generate(
            participant_id=payload.participant_id,
            condition_key=payload.condition_key,
            message=payload.message,
        )
        return ChatSendResponse(
            participant_id=payload.participant_id,
            condition_key=payload.condition_key,
            reply=session.messages[-1]["content"],
            messages=session.messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}",
        )
    finally:
        await _release_inflight(payload.participant_id, payload.condition_key)


@app.post(
    "/api/v1/chat/reset/{participant_id}/{condition_key}",
    response_model=ChatResetResponse,
)
async def reset_chat_history(participant_id: str, condition_key: str):
    try:
        session = await clear_chat_session(participant_id, condition_key)
        return ChatResetResponse(
            success=True,
            participant_id=participant_id,
            condition_key=session.condition_key,
            messages=session.messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset chat history: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
