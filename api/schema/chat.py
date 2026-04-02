from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


ConditionKey = Literal[
    "teams_personalized",
    "teams_non_personalized",
    "plastic_personalized",
    "plastic_non_personalized",
    "pe_personalized",
    "pe_non_personalized",
    "control",
]


class ConditionDescriptor(BaseModel):
    key: ConditionKey
    label: str
    topic: str
    statement: str
    personalized: bool
    is_control: bool
    requires_user_answer: bool
    requires_argument: bool


class ConditionsResponse(BaseModel):
    conditions: List[ConditionDescriptor]


class ChatSendRequest(BaseModel):
    prolific_id: str = Field(..., min_length=1, description="Prolific participant identifier")
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    client_message_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Client-generated idempotency key for this user message",
    )


class ChatMessageResponse(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    prolific_id: str
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    messages: List[ChatMessageResponse]


class ChatSendResponse(BaseModel):
    prolific_id: str
    condition_key: ConditionKey
    reply: str
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class ChatResetResponse(BaseModel):
    success: bool
    prolific_id: str
    condition_key: ConditionKey
    messages: List[ChatMessageResponse]
