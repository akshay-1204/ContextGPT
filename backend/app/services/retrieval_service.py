"""Vector similarity retrieval and RAG context construction service."""

import math
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.models.chunk import DocumentChunk
from backend.app.db.models.source import Source
from backend.app.services.embedding_service import EmbeddingService

try:
    from langchain_community.vectorstores import PGVector
except ImportError:
    PGVector = None


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    def retrieve_relevant_chunks(
        self,
        query: str,
        user_id: int,
        source_id: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant chunks strictly owned by user_id.
        Applies optional source_id filter.
        """
        k = top_k or settings.RETRIEVAL_TOP_K
        query_vector = self.embedding_service.generate_embedding(query)

        # Build query strictly scoped to authenticated user
        stmt = select(DocumentChunk).where(DocumentChunk.user_id == user_id)
        if source_id is not None:
            stmt = stmt.where(DocumentChunk.source_id == source_id)

        all_chunks = self.db.execute(stmt).scalars().all()
        if not all_chunks:
            return []

        scored_chunks = []
        for chunk in all_chunks:
            vector = chunk.embedding_json
            if vector:
                score = cosine_similarity(query_vector, vector)
                scored_chunks.append({
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.chunk_text,
                    "score": float(score),
                    "metadata": chunk.chunk_metadata or {},
                })

        # Sort descending by similarity score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_chunks[:k]

        # Enrich with source titles & references
        enriched = []
        for item in top_results:
            source = self.db.execute(
                select(Source).where(Source.id == item["source_id"])
            ).scalar_one_or_none()

            source_title = source.title if source else f"Source #{item['source_id']}"
            source_ref = source.source_reference if source else ""
            source_type = source.source_type if source else "unknown"

            enriched.append({
                **item,
                "source_title": source_title,
                "source_reference": source_ref,
                "source_type": source_type,
            })

        return enriched

    def construct_context(self, retrieved_chunks: List[Dict[str, Any]], max_chars: int = 12000) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Builds bounded context string from retrieved chunks and collects reference citations.
        """
        context_blocks = []
        references = []
        current_len = 0

        for idx, item in enumerate(retrieved_chunks):
            passage_label = f"[Source {idx + 1}: {item['source_title']} (Section/Chunk {item['chunk_index'] + 1})]"
            block = f"{passage_label}\n{item['text']}\n"

            if current_len + len(block) > max_chars:
                break

            context_blocks.append(block)
            current_len += len(block)

            references.append({
                "citation_label": f"[Source {idx + 1}]",
                "source_id": item["source_id"],
                "source_title": item["source_title"],
                "source_reference": item["source_reference"],
                "source_type": item["source_type"],
                "chunk_index": item["chunk_index"],
                "similarity_score": round(item["score"], 4),
            })

        bounded_context = "\n---\n".join(context_blocks)
        return bounded_context, references
