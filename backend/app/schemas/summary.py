"""Summary schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


SummaryTypeLiteral = Literal[
    "short",
    "detailed",
    "bullet_points",
    "key_takeaways",
    "custom",
]


class SummaryCreate(BaseModel):
    source_id: int = Field(..., description="ID of the uploaded/processed source to summarize")
    summary_type: SummaryTypeLiteral = Field(default="short", description="Style of summary to generate")
    custom_instructions: Optional[str] = Field(None, max_length=1000, description="Optional custom guidelines for LLM")
    title: Optional[str] = Field(None, max_length=255)


class SummaryResponse(BaseModel):
    id: int
    user_id: int
    source_id: Optional[int]
    title: str
    summary_text: str
    summary_type: str
    model_name: str
    token_usage: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
