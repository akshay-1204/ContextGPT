"""Chat, RAG, and Conversation schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ChatQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="User question to answer via RAG")
    conversation_id: Optional[int] = Field(None, description="Optional existing conversation ID to continue")
    source_id: Optional[int] = Field(None, description="Optional filter to scope retrieval to a specific source")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    source_references: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatAnswerResponse(BaseModel):
    conversation_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    source_references: List[Dict[str, Any]]
    is_grounded: bool


class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=255)
    source_id: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    source_id: Optional[int]
    title: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
