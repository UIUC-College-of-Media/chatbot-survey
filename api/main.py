import asyncio
import os
from datetime import UTC, datetime

import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #TODO: In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "persuasive_ai_study")

_client = None
_db = None
_survey1_collection = None
_participants_collection = None
_chat_messages_collection = None
# Process-local guard for "one active generation per participant" in local dev.
_inflight_participants = set()
_inflight_lock = asyncio.Lock()

def get_database():
    """Get database connection, reusing existing connection for serverless"""
    global _client, _db, _survey1_collection, _participants_collection, _chat_messages_collection
    
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URL,
            maxPoolSize=10,  
            minPoolSize=1,   
            serverSelectionTimeoutMS=5000  
        )
        _db = _client[DATABASE_NAME]
        _survey1_collection = _db["survey1_responses"]
        _participants_collection = _db["participants"]
        _chat_messages_collection = _db["chat_messages"]
    
    return _client, _db, _survey1_collection


def get_chat_collections():
    """Return Mongo collections used by the chat feature."""
    client, db, _ = get_database()
    return client, db["participants"], db["chat_messages"]


async def participant_exists(participants_collection, participant_id: str) -> bool:
    participant = await participants_collection.find_one(
        {"participant_id": participant_id, "status": {"$ne": "disabled"}}
    )
    return participant is not None


async def list_chat_messages(chat_messages_collection, participant_id: str):
    cursor = chat_messages_collection.find({"participant_id": participant_id}).sort(
        "created_at", 1
    )
    return await cursor.to_list(length=1000)


def _serialize_chat_message(document: dict) -> ChatMessageResponse:
    return ChatMessageResponse(
        role=document["role"],
        content=document["content"],
        created_at=document["created_at"],
    )

async def _acquire_inflight(participant_id: str) -> bool:
    # Atomically mark a participant as "busy" so concurrent sends return 409.
    async with _inflight_lock:
        if participant_id in _inflight_participants:
            return False
        _inflight_participants.add(participant_id)
        return True


async def _release_inflight(participant_id: str) -> None:
    # Always clear the busy flag after request completion/error.
    async with _inflight_lock:
        _inflight_participants.discard(participant_id)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Persuasive AI Study API",
        "version": "1.0.0",
        "endpoints": {
            "survey1": "/api/v1/survey1",
            "chat_send": "/api/v1/chat/send",
            "chat_history": "/api/v1/chat/history/{participant_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client, db, survey1_collection = get_database()
        await client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@app.post("/api/v1/survey1", response_model=Survey1Response, status_code=status.HTTP_201_CREATED)
async def submit_survey1(survey_data: Survey1Request):
    """
    Submit Survey 1 responses
    
    This endpoint receives responses from Qualtrics survey and stores them in MongoDB.
    """
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
            "created_at": datetime.utcnow(),
            "survey_type": "survey1_baseline",
            "week": 0
        }
        
        result = await survey1_collection.insert_one(document)
        
        return Survey1Response(
            success=True,
            message="Survey 1 response stored successfully",
            participant_id=survey_data.participant_id,
            survey_id=str(result.inserted_id),
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store survey response: {str(e)}"
        )


@app.get("/api/v1/chat/history/{participant_id}", response_model=ChatHistoryResponse)
async def get_chat_history(participant_id: str):
    """Return a participant's single-session chat history."""
    try:
        _, participants_collection, chat_messages_collection = get_chat_collections()

        if not await participant_exists(participants_collection, participant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown participant_id",
            )

        documents = await list_chat_messages(chat_messages_collection, participant_id)
        messages = [_serialize_chat_message(doc) for doc in documents]
        return ChatHistoryResponse(participant_id=participant_id, messages=messages)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}",
        )


@app.post("/api/v1/chat/send", response_model=ChatSendResponse)
async def send_chat_message(payload: ChatSendRequest):
    """Send a user message, call the LLM, persist the transcript, and return the reply."""
    acquired = await _acquire_inflight(payload.participant_id)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A response is already being generated for this participant",
        )

    try:
        _, participants_collection, chat_messages_collection = get_chat_collections()

        if not await participant_exists(participants_collection, payload.participant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown participant_id",
            )

        now = datetime.now(UTC)
        user_message_doc = {
            "participant_id": payload.participant_id,
            "role": "user",
            "content": payload.message,
            "created_at": now,
        }
        await chat_messages_collection.insert_one(user_message_doc)

        history_docs = await list_chat_messages(chat_messages_collection, payload.participant_id)
        assistant_text = await generate_chat_reply(
            participant_id=payload.participant_id,
            messages=[
                {"role": doc["role"], "content": doc["content"]}
                for doc in history_docs
            ],
        )

        assistant_doc = {
            "participant_id": payload.participant_id,
            "role": "assistant",
            "content": assistant_text,
            "created_at": datetime.now(UTC),
        }
        await chat_messages_collection.insert_one(assistant_doc)

        all_docs = await list_chat_messages(chat_messages_collection, payload.participant_id)
        return ChatSendResponse(
            participant_id=payload.participant_id,
            reply=assistant_text,
            messages=[_serialize_chat_message(doc) for doc in all_docs],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}",
        )
    finally:
        await _release_inflight(payload.participant_id)


@app.post("/api/v1/chat/reset/{participant_id}")
async def reset_chat_history(participant_id: str):
    """Development-only helper to clear chat history for a participant."""
    try:
        _, participants_collection, chat_messages_collection = get_chat_collections()
        if not await participant_exists(participants_collection, participant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown participant_id",
            )

        await chat_messages_collection.delete_many({"participant_id": participant_id})
        return {"success": True, "participant_id": participant_id}
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
