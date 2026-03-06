from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    participant_id: str = Field(..., min_length=1, description="Participant identifier")
    message: str = Field(..., min_length=1, max_length=4000, description="User message")


class ChatMessageResponse(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    participant_id: str
    messages: List[ChatMessageResponse]


class ChatSendResponse(BaseModel):
    participant_id: str
    reply: str
    messages: List[ChatMessageResponse]
