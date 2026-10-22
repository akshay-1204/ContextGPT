"""Embedding generation and Document Chunking Service."""

import math
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models.chunk import DocumentChunk


def create_fallback_embedding(text: str, dim: int = 1536) -> List[float]:
    """
    Deterministic normalized pseudo-embedding vector for offline / testing / keyless usage.
    Ensures that RAG retrieval math and cosine similarity work seamlessly in test environments.
    """
    vector = [0.0] * dim
    words = text.lower().split()
    if not words:
        words = ["empty"]

    for i, word in enumerate(words):
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vector[idx] += 1.0 / (1.0 + (i % 10))

    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    else:
        vector[0] = 1.0

    return vector


class EmbeddingService:
    def __init__(self, db: Session):
        self.db = db
        self._embedding_failed = False

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> List[str]:
        """Split document text into bounded, overlapping chunks."""
        size = chunk_size or settings.CHUNK_SIZE
        overlap = chunk_overlap or settings.CHUNK_OVERLAP

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            chunks = splitter.split_text(text)
            return [c.strip() for c in chunks if c.strip()]
        except Exception:
            chunks = []
            start = 0
            text_len = len(text)
            step = max(size - overlap, 50)
            while start < text_len:
                chunk = text[start: start + size].strip()
                if chunk:
                    chunks.append(chunk)
                start += step
            return chunks

    def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector using OpenAI, or fallback to deterministic offline embedding."""
        if not settings.OPENAI_API_KEY or self._embedding_failed:
            return create_fallback_embedding(text)

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL or None,
                timeout=4.0,
                max_retries=0,
            )

            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text.replace("\n", " "),
            )
            return response.data[0].embedding
        except Exception as e:
            self._embedding_failed = True
            logger.warning(f"Embedding API unavailable ({e}); switching to deterministic offline vectors.")
            return create_fallback_embedding(text)

    def process_and_store_source_chunks(
        self,
        source_id: int,
        user_id: int,
        full_text: str,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Chunks source text, computes embeddings, and stores document chunks in DB."""
        chunks_text = self.chunk_text(full_text)
        if not chunks_text:
            return []

        stored_chunks = []
        for idx, chunk_str in enumerate(chunks_text):
            vector = self.generate_embedding(chunk_str)
            chunk_record = DocumentChunk(
                source_id=source_id,
                user_id=user_id,
                chunk_index=idx,
                chunk_text=chunk_str,
                embedding_json=vector,
                chunk_metadata={
                    **(source_metadata or {}),
                    "chunk_index": idx,
                    "total_chunks": len(chunks_text),
                    "char_count": len(chunk_str),
                },
            )
            self.db.add(chunk_record)
            stored_chunks.append(chunk_record)

        self.db.commit()
        return stored_chunks
