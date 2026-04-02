from datetime import UTC, datetime
from typing import Literal

from beanie import Document, Indexed
from pydantic import BaseModel, Field

from api.schema.chat import ConditionKey
from api.services.condition_chat import ChatSession


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatSessionDocument(Document):
    prolific_id: Indexed(str, unique=True)
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    system_prompt: str
    messages: list[ChatMessage] = Field(default_factory=list)
    inflight_until: datetime | None = None
    inflight_request_id: str | None = None
    last_client_message_id: str | None = None
    last_user_message: ChatMessage | None = None
    last_assistant_message: ChatMessage | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "chat_sessions"

    def to_service(self) -> ChatSession:
        return ChatSession(
            prolific_id=self.prolific_id,
            condition_key=self.condition_key,
            condition_label=self.condition_label,
            topic=self.topic,
            statement=self.statement,
            system_prompt=self.system_prompt,
            messages=[m.model_dump() for m in self.messages],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_service(cls, session: ChatSession) -> "ChatSessionDocument":
        return cls(
            prolific_id=session.prolific_id,
            condition_key=session.condition_key,
            condition_label=session.condition_label,
            topic=session.topic,
            statement=session.statement,
            system_prompt=session.system_prompt,
            messages=[ChatMessage(**m) for m in session.messages],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
