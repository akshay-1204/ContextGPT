"""Application Configuration Module using Pydantic Settings."""

import os
from typing import List, Union, Optional
from pydantic import Field, field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application details
    APP_NAME: str = "ContextGPT"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # AI & LLM Model Configuration (Supports OpenAI, NVIDIA NIM, Groq, Ollama)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="Optional custom base URL for OpenAI-compatible providers like NVIDIA NIM (https://integrate.api.nvidia.com/v1)"
    )
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"


    # Database Configuration (PostgreSQL only)
    POSTGRES_DB: str = "contextgpt"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/contextgpt",
        description="PostgreSQL SQLAlchemy database URL (postgresql+psycopg://)."
    )


    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="default-contextgpt-secret-key-change-me-in-production-32chars",
        description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Networking & CORS
    API_BASE_URL: str = "http://localhost:8000"
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Content & RAG Settings
    MAX_UPLOAD_SIZE_MB: int = 20
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 5

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
