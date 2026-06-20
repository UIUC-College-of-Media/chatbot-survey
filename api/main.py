import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import motor.motor_asyncio
from beanie import init_beanie
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from api.config import get_settings
from api.models import ChatMessage, ChatSessionDocument, LLMConfigDocument, Survey1Document
from api.services.llm_config_cache import get_llm_config
from api.schema.chat import (
    ChatResetResponse,
    ChatSendRequest,
    ChatSessionResponse,
    ConditionsResponse,
)
from api.schema.survey import Survey1GetResponse, Survey1Request, Survey1Response, Survey3Request, Survey3Response
from api.services.condition_chat import (
    clear_chat_session,
    condition_metadata,
    initialize_chat_session,
)

load_dotenv()

settings = get_settings()

_client = None
_db = None

LOCK_TIMEOUT_SECONDS = 60


async def init_database() -> None:
    """Initialize MongoDB client and Beanie documents."""
    global _client, _db

    if _client is not None:
        return

    _client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.mongodb_url,
        maxPoolSize=10,
        minPoolSize=1,
        serverSelectionTimeoutMS=5000,
    )
    _db = _client[settings.database_name]
    await init_beanie(
        database=_db,
        document_models=[Survey1Document, ChatSessionDocument, LLMConfigDocument],
    )


async def close_database() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_database():
    """Return initialized database client and db handle."""
    if _client is None or _db is None:
        raise RuntimeError("Database is not initialized")
    return _client, _db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    try:
        await get_llm_config()  # warm cache at startup, non-fatal if not configured yet
    except RuntimeError:
        pass
    try:
        yield
    finally:
        await close_database()


app = FastAPI(
    title="Persuasive AI Study API",
    description="API for collecting and storing survey responses for the Persuasive AI study",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _acquire_inflight(prolific_id: str, request_id: str) -> bool:
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=LOCK_TIMEOUT_SECONDS)
    collection = ChatSessionDocument.get_motor_collection()
    result = await collection.find_one_and_update(
        {
            "prolific_id": prolific_id,
            "$or": [
                {"inflight_until": {"$exists": False}},
                {"inflight_until": None},
                {"inflight_until": {"$lt": now}},
            ],
        },
        {
            "$set": {
                "inflight_until": expires_at,
                "inflight_request_id": request_id,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return result is not None


async def _release_inflight(prolific_id: str, request_id: str) -> None:
    collection = ChatSessionDocument.get_motor_collection()
    await collection.update_one(
        {"prolific_id": prolific_id, "inflight_request_id": request_id},
        {"$set": {"inflight_until": None, "inflight_request_id": None}},
    )


def _to_chat_session_response(session: ChatSessionDocument) -> ChatSessionResponse:
    return ChatSessionResponse(
        prolific_id=session.prolific_id,
        condition_key=session.condition_key,
        condition_label=session.condition_label,
        topic=session.topic,
        statement=session.statement,
        messages=[msg.model_dump() for msg in session.messages],
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


@app.get("/livez")
async def liveness_check():
    """Process-level health check for container liveness."""
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC),
    }


@app.get("/readyz")
async def readiness_check():
    """Dependency health check for Kubernetes readiness."""
    try:
        client, _ = get_database()
        await client.admin.command("ping")
        return {
            "status": "ready",
            "database": "connected",
            "timestamp": datetime.now(UTC),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Backward-compatible alias for readiness checks."""
    return await readiness_check()


@app.post(
    "/api/v1/survey1",
    response_model=Survey1Response,
    status_code=status.HTTP_201_CREATED,
)
async def submit_survey1(survey_data: Survey1Request):
    """Submit Survey 1 responses from Qualtrics. Idempotent on prolific_id."""
    if not survey_data.prolific_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prolific_id is required",
        )

    prolific_id = survey_data.prolific_id
    document = Survey1Document.from_request(survey_data)
    doc_dict = document.model_dump(exclude={"id"})

    collection = Survey1Document.get_motor_collection()
    result = await collection.find_one_and_update(
        {"prolific_id": prolific_id},
        {"$set": doc_dict},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return Survey1Response(
        success=True,
        message="Survey 1 response stored successfully",
        participant_id=result.get("participant_id", survey_data.participant_id),
        survey_id=str(result.get("_id", "")),
        timestamp=result.get("created_at", datetime.now(UTC)),
    )


@app.get("/api/v1/survey1/data", response_model=Survey1GetResponse)
async def get_survey1_data(
    prolific_id: str = Query(..., description="Prolific participant ID"),
):
    """Return the pre-block metadata (topic, personalization, is_control) for a Survey 1 participant."""
    survey = await Survey1Document.find_one({"prolific_id": prolific_id})
    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Survey 1 response found for this prolific_id",
        )
    pre_block = survey.pre_block
    return Survey1GetResponse(
        topic=pre_block.topic if pre_block else None,
        personalization=pre_block.personalization if pre_block else None,
        is_control=pre_block.is_control if pre_block else None,
    )


def _derive_condition_key(
    pre_topic: str | None,
    pre_personalization: str | None,
    pre_is_control: bool | None,
) -> str:
    if pre_is_control or pre_personalization == "control":
        return "control"
    prefix = {"teams": "teams", "plastic_ban": "plastic", "pe_mandatory": "pe"}.get(pre_topic or "")
    if not prefix:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot derive condition from pre_topic={pre_topic!r}",
        )
    if pre_personalization == "personalized":
        return f"{prefix}_personalized"
    if pre_personalization == "non_personalized":
        return f"{prefix}_non_personalized"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Cannot derive condition from pre_personalization={pre_personalization!r}",
    )


@app.get("/api/v1/chat/start", response_model=ChatSessionResponse)
async def start_chat_from_survey(
    prolific_id: str = Query(..., description="Prolific participant ID from iframe URL"),
):
    """Return existing chat session if one exists, otherwise initialize from Survey 1.
    Returns 403 if the participant has not submitted Survey 1."""
    survey = await Survey1Document.find_one({"prolific_id": prolific_id})
    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant has not completed Survey 1",
        )

    existing = await ChatSessionDocument.find_one({"prolific_id": prolific_id})
    if existing is not None:
        return _to_chat_session_response(existing)

    pre_block = survey.pre_block
    if pre_block is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Survey 1 is missing randomized block metadata",
        )
    condition_key = _derive_condition_key(
        pre_topic=pre_block.topic,
        pre_personalization=pre_block.personalization,
        pre_is_control=pre_block.is_control,
    )
    block_responses = pre_block.responses

    session = initialize_chat_session(
        prolific_id=prolific_id,
        condition_key=condition_key,
        user_answer=block_responses.opinion if block_responses else None,
        argument=block_responses.opinion_reason if block_responses else None,
    )
    session_doc = ChatSessionDocument.from_service(session)

    try:
        await session_doc.insert()
    except DuplicateKeyError:
        existing = await ChatSessionDocument.find_one({"prolific_id": prolific_id})
        if existing is None:
            raise
        return _to_chat_session_response(existing)

    return _to_chat_session_response(session_doc)


@app.get("/api/v1/chat/session/{prolific_id}", response_model=ChatSessionResponse)
async def get_chat_session(prolific_id: str):
    try:
        doc = await ChatSessionDocument.find_one({"prolific_id": prolific_id})
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Chat session not initialized for this participant",
            )
        return _to_chat_session_response(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat session: {str(e)}",
        )


@app.get("/api/v1/chat/conditions", response_model=ConditionsResponse)
async def get_conditions():
    return ConditionsResponse(conditions=condition_metadata())


@app.post("/api/v1/chat/stream")
async def stream_chat_message(payload: ChatSendRequest):
    from api.services.llm import stream_chat_reply

    request_id = payload.client_message_id

    # Pre-lock idempotency check
    doc = await ChatSessionDocument.find_one({"prolific_id": payload.prolific_id})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chat session not initialized for this participant",
        )

    if (
        doc.last_client_message_id == request_id
        and doc.last_user_message is not None
        and doc.last_assistant_message is not None
    ):
        async def _replay():
            yield _sse({
                "done": True,
                "user_message": doc.last_user_message.model_dump(mode="json"),
                "assistant_message": doc.last_assistant_message.model_dump(mode="json"),
            })
        return StreamingResponse(_replay(), media_type="text/event-stream")

    acquired = await _acquire_inflight(payload.prolific_id, request_id)
    if not acquired:
        latest = await ChatSessionDocument.find_one({"prolific_id": payload.prolific_id})
        if (
            latest is not None
            and latest.last_client_message_id == request_id
            and latest.last_user_message is not None
            and latest.last_assistant_message is not None
        ):
            async def _replay2():
                yield _sse({
                    "done": True,
                    "user_message": latest.last_user_message.model_dump(mode="json"),
                    "assistant_message": latest.last_assistant_message.model_dump(mode="json"),
                })
            return StreamingResponse(_replay2(), media_type="text/event-stream")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A response is already being generated for this participant",
        )

    # Lock acquired — any exception before returning StreamingResponse must release the lock
    try:
        doc = await ChatSessionDocument.find_one({"prolific_id": payload.prolific_id})
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Chat session not initialized for this participant",
            )

        if (
            doc.last_client_message_id == request_id
            and doc.last_user_message is not None
            and doc.last_assistant_message is not None
        ):
            await _release_inflight(payload.prolific_id, request_id)
            async def _replay3():
                yield _sse({
                    "done": True,
                    "user_message": doc.last_user_message.model_dump(mode="json"),
                    "assistant_message": doc.last_assistant_message.model_dump(mode="json"),
                })
            return StreamingResponse(_replay3(), media_type="text/event-stream")

        now = datetime.now(UTC)
        user_msg = ChatMessage(role="user", content=payload.message, created_at=now)
        doc.messages.append(user_msg)
        doc.updated_at = now
        doc.last_client_message_id = request_id
        doc.last_user_message = user_msg
        await doc.save()

        messages_for_llm = [{"role": m.role, "content": m.content} for m in doc.messages]
        system_prompt = doc.system_prompt

    except HTTPException:
        await _release_inflight(payload.prolific_id, request_id)
        raise
    except Exception as e:
        await _release_inflight(payload.prolific_id, request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare stream: {str(e)}",
        )

    async def _generate():
        accumulated = []
        try:
            async for token in stream_chat_reply(system_prompt, messages_for_llm):
                accumulated.append(token)
                yield _sse({"chunk": token})

            assistant_content = "".join(accumulated)
            if not assistant_content:
                yield _sse({"error": "LLM returned empty assistant content"})
                return

            finished_at = datetime.now(UTC)
            assistant_msg = ChatMessage(role="assistant", content=assistant_content, created_at=finished_at)
            doc.messages.append(assistant_msg)
            doc.updated_at = finished_at
            doc.last_assistant_message = assistant_msg
            await doc.save()

            yield _sse({
                "done": True,
                "user_message": user_msg.model_dump(mode="json"),
                "assistant_message": assistant_msg.model_dump(mode="json"),
            })
        except Exception as exc:
            yield _sse({"error": str(exc)})
        finally:
            await _release_inflight(payload.prolific_id, request_id)

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.post(
    "/api/v1/chat/reset/{prolific_id}",
    response_model=ChatResetResponse,
)
async def reset_chat_history(prolific_id: str):
    try:
        doc = await ChatSessionDocument.find_one({"prolific_id": prolific_id})
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Chat session not initialized for this participant",
            )

        session = clear_chat_session(doc.to_service())
        doc.messages = [msg for msg in ChatSessionDocument.from_service(session).messages]
        doc.updated_at = session.updated_at
        await doc.save()

        return ChatResetResponse(
            success=True,
            prolific_id=prolific_id,
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
