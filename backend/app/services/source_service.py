"""Source ingestion, validation, processing, and management service."""

import os
import shutil
import tempfile
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models.source import Source
from backend.app.loaders.loader_registry import LoaderRegistry
from backend.app.loaders.base import LoaderError
from backend.app.services.embedding_service import EmbeddingService


class SourceService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    def get_user_sources(self, user_id: int) -> List[Source]:
        """Fetch all sources owned by the specified user."""
        stmt = select(Source).where(Source.user_id == user_id).order_by(Source.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_user_source(self, user_id: int, source_id: int) -> Optional[Source]:
        """Fetch a specific source ensuring user ownership."""
        stmt = select(Source).where(Source.id == source_id, Source.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_user_source(self, user_id: int, source_id: int) -> bool:
        """Deletes a source and cascades deletion to chunks and summaries."""
        source = self.get_user_source(user_id, source_id)
        if not source:
            return False
        self.db.delete(source)
        self.db.commit()
        return True

    def process_and_save_source(
        self,
        user_id: int,
        source_type: str,
        source_reference: str,
        original_filename: Optional[str] = None,
        title: Optional[str] = None,
        initial_metadata: Optional[Dict[str, Any]] = None,
    ) -> Source:
        """Core pipeline: validate source, extract text, store source record, and trigger vector chunking."""
        source = Source(
            user_id=user_id,
            source_type=source_type,
            original_filename=original_filename,
            source_reference=source_reference,
            title=title or original_filename or source_reference[:50],
            content_metadata=initial_metadata or {},
            processing_status="processing",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        try:
            loader = LoaderRegistry.get_loader(source_type)
            extracted_text, enriched_meta = loader.extract(
                source_reference=source_reference,
                metadata=initial_metadata or {},
            )

            # Update title if loader discovered a better one (e.g., from HTML title tag)
            inferred_title = enriched_meta.get("title") or title or original_filename or f"{source_type.upper()} Source"

            source.title = str(inferred_title)[:255]
            source.extracted_text = extracted_text
            source.content_metadata = enriched_meta
            source.processing_status = "completed"
            self.db.commit()

            # Trigger RAG chunking and vector storage
            self.embedding_service.process_and_store_source_chunks(
                source_id=source.id,
                user_id=user_id,
                full_text=extracted_text,
                source_metadata=enriched_meta,
            )

        except LoaderError as le:
            logger.warning(f"Loader error for source #{source.id}: {le}")
            source.processing_status = "failed"
            source.error_message = str(le)
            self.db.commit()
        except Exception as e:
            logger.exception(f"Unexpected extraction failure for source #{source.id}: {e}")
            source.processing_status = "failed"
            source.error_message = f"Processing error: {str(e)}"
            self.db.commit()

        self.db.refresh(source)
        return source

    async def handle_file_upload(
        self,
        user_id: int,
        file: UploadFile,
        title: Optional[str] = None,
    ) -> Source:
        """Validates uploaded file size and extension, saves safely to temporary storage, and processes."""
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if not ext:
            raise ValueError("Uploaded file has no extension.")

        # Determine source type
        ext_to_type = {
            "pdf": "pdf",
            "txt": "txt",
            "text": "txt",
            "md": "txt",
            "csv": "csv",
            "docx": "docx",
            "xlsx": "xlsx",
            "xls": "xlsx",
            "json": "json",
            "xml": "xml",
            "png": "image",
            "jpg": "image",
            "jpeg": "image",
            "webp": "image",
        }
        source_type = ext_to_type.get(ext)
        if not source_type:
            supported = ", ".join(sorted(ext_to_type.keys()))
            raise ValueError(f"Unsupported file extension '.{ext}'. Supported extensions: {supported}")

        # Check file size limit
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        temp_dir = tempfile.mkdtemp(prefix="contextgpt_upload_")
        temp_path = os.path.join(temp_dir, filename)

        try:
            total_bytes = 0
            with open(temp_path, "wb") as out_file:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise ValueError(f"File size exceeds maximum upload limit of {settings.MAX_UPLOAD_SIZE_MB}MB.")
                    out_file.write(chunk)

            source = self.process_and_save_source(
                user_id=user_id,
                source_type=source_type,
                source_reference=temp_path,
                original_filename=filename,
                title=title or filename,
                initial_metadata={"original_filename": filename, "file_size_bytes": total_bytes},
            )
            return source
        finally:
            # Clean up temp file safely
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
