"""Source schemas."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class SourceCreate(BaseModel):
    source_type: str = Field(..., max_length=50)
    source_reference: str = Field(..., max_length=1000)
    title: Optional[str] = Field(None, max_length=255)
    content_metadata: Optional[Dict[str, Any]] = None


class WebpageSourceCreate(BaseModel):
    url: str = Field(..., description="HTTP or HTTPS URL to extract content from")
    title: Optional[str] = Field(None, max_length=255)


class APISourceCreate(BaseModel):
    endpoint_url: str = Field(..., description="HTTP or HTTPS API endpoint to query")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional custom HTTP headers (e.g., Bearer auth)")
    title: Optional[str] = Field(None, max_length=255)


class URLSourceCreate(BaseModel):
    url: str = Field(..., description="Any HTTP or HTTPS URL to fetch and extract content from (JSON API, webpage, plain text)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional custom HTTP headers for authenticated endpoints")
    title: Optional[str] = Field(None, max_length=255)


class DatabaseSourceCreate(BaseModel):
    connection_string: str = Field(..., description="Database connection URI, e.g. postgresql://user:pass@host:port/dbname or sqlite:///file.db")
    query: str = Field(..., description="SELECT query to extract data")
    title: Optional[str] = Field(None, max_length=255)


class YouTubeSourceCreate(BaseModel):
    url: str = Field(..., description="YouTube video URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)")
    title: Optional[str] = Field(None, max_length=255)



class SourceResponse(BaseModel):
    id: int
    user_id: int
    source_type: str
    original_filename: Optional[str]
    source_reference: str
    title: Optional[str]
    content_metadata: Optional[Dict[str, Any]]
    processing_status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
