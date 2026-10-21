"""Source database model."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.db.models.user import User
    from backend.app.db.models.summary import Summary
    from backend.app.db.models.conversation import Conversation
    from backend.app.db.models.chunk import DocumentChunk


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, txt, webpage, api, database, etc.
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sources")
    summaries: Mapped[List["Summary"]] = relationship("Summary", back_populates="source", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="source")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="source", cascade="all, delete-orphan")
