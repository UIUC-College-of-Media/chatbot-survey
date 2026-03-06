from datetime import datetime
from typing import List, Literal, Optional

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


class ChatInitializeRequest(BaseModel):
    participant_id: str = Field(..., min_length=1, description="Participant identifier")
    condition_key: ConditionKey
    user_answer: Optional[int] = Field(None, ge=1, le=6)
    argument: Optional[str] = None


class ChatSendRequest(BaseModel):
    participant_id: str = Field(..., min_length=1, description="Participant identifier")
    condition_key: ConditionKey
    message: str = Field(..., min_length=1, max_length=4000, description="User message")


class ChatMessageResponse(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatSessionSummary(BaseModel):
    participant_id: str
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    updated_at: datetime


class ChatSessionResponse(BaseModel):
    participant_id: str
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    messages: List[ChatMessageResponse]


class ChatSessionsResponse(BaseModel):
    participant_id: str
    sessions: List[ChatSessionSummary]


class ChatSendResponse(BaseModel):
    participant_id: str
    condition_key: ConditionKey
    reply: str
    messages: List[ChatMessageResponse]


class ChatResetResponse(BaseModel):
    success: bool
    participant_id: str
    condition_key: ConditionKey
    messages: List[ChatMessageResponse]
