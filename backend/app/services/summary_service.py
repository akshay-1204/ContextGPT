"""Summarization service supporting direct, custom, and hierarchical map-reduce workflows."""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models.source import Source
from backend.app.db.models.summary import Summary
from backend.app.prompts.summarization import (
    get_summarization_prompt,
    get_chunk_summary_prompt,
    COMBINE_SUMMARIES_PROMPT,
)
from backend.app.services.embedding_service import EmbeddingService


class SummaryService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    def _call_llm(self, system_prompt: str, user_content: str) -> Tuple[str, Dict[str, Any]]:
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL

        # Dynamic live check: if cached settings was empty at boot, re-read .env file live
        if not api_key:
            from dotenv import dotenv_values
            env_map = dotenv_values(".env")
            api_key = env_map.get("OPENAI_API_KEY") or ""
            base_url = env_map.get("OPENAI_BASE_URL") or base_url
            model = env_map.get("OPENAI_MODEL") or model

        if not api_key:
            logger.info("OPENAI_API_KEY is missing. Providing extractive summary.")
            # Extractive fallback summary for offline / testing
            lines = [l.strip() for l in user_content.splitlines() if l.strip()]
            preview = lines[:8]
            fallback_text = (
                "**[ContextGPT Offline Demonstration Summary]**\n\n"
                f"*(Note: OPENAI_API_KEY is not configured in .env. Showing extracted text overview)*\n\n"
                + "\n\n".join(f"- {p}" for p in preview)
            )
            return fallback_text, {"model": "offline-fallback", "prompt_tokens": 0, "completion_tokens": 0}

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url=base_url or None,
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )

            summary_content = response.choices[0].message.content or ""
            usage = {
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
            return summary_content, usage
        except Exception as e:
            logger.warning(f"OpenAI completion error ({e}); providing extracted fallback summary.")
            lines = [l.strip() for l in user_content.splitlines() if l.strip()]
            preview = lines[:8]
            fallback_text = (
                "**[ContextGPT Document Summary]**\n\n"
                f"*(Note: OpenAI API error: '{e}'. Showing extracted content overview)*\n\n"
                + "\n\n".join(f"- {p}" for p in preview)
            )
            return fallback_text, {"model": "fallback-overview", "prompt_tokens": 0, "completion_tokens": 0}


    def summarize_source(
        self,
        user_id: int,
        source_id: int,
        summary_type: str = "short",
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Summary:
        # Validate source ownership
        stmt = select(Source).where(Source.id == source_id, Source.user_id == user_id)
        source = self.db.execute(stmt).scalar_one_or_none()
        if not source:
            raise ValueError(f"Source #{source_id} not found or you do not have permission to access it.")

        if not source.extracted_text or not source.extracted_text.strip():
            raise ValueError("This source does not contain any extracted text to summarize.")

        text_to_summarize = source.extracted_text.strip()
        system_prompt = get_summarization_prompt(
            summary_type=summary_type,
            custom_instructions=custom_instructions,
            source_type=source.source_type,
        )

        # Context boundary: ~16,000 characters (approx 4,000 tokens)
        MAX_DIRECT_CHARS = 16000

        if len(text_to_summarize) <= MAX_DIRECT_CHARS:
            # Direct single-pass summarization
            summary_text, usage = self._call_llm(system_prompt, text_to_summarize)
        else:
            # Hierarchical Map-Reduce summarization for long documents
            chunks = self.embedding_service.chunk_text(text_to_summarize, chunk_size=8000, chunk_overlap=400)
            intermediate_summaries = []
            chunk_prompt = get_chunk_summary_prompt(source_type=source.source_type)

            total_prompt_tok = 0
            total_comp_tok = 0

            for c in chunks[:8]:  # Guard against massive abuse
                c_summary, c_usage = self._call_llm(chunk_prompt, c)
                intermediate_summaries.append(c_summary)
                total_prompt_tok += c_usage.get("prompt_tokens", 0)
                total_comp_tok += c_usage.get("completion_tokens", 0)

            combined_chunks_text = "\n\n---\n\n".join(intermediate_summaries)
            final_prompt = f"{system_prompt}\n\n{COMBINE_SUMMARIES_PROMPT}"
            summary_text, final_usage = self._call_llm(final_prompt, combined_chunks_text)

            usage = {
                "model": final_usage.get("model", settings.OPENAI_MODEL),
                "prompt_tokens": total_prompt_tok + final_usage.get("prompt_tokens", 0),
                "completion_tokens": total_comp_tok + final_usage.get("completion_tokens", 0),
                "hierarchical": True,
                "sections_processed": len(chunks),
            }

        summary_title = title or f"{summary_type.capitalize()} Summary: {source.title or 'Document'}"

        summary_record = Summary(
            user_id=user_id,
            source_id=source.id,
            title=summary_title[:255],
            summary_text=summary_text,
            summary_type=summary_type,
            model_name=usage.get("model", settings.OPENAI_MODEL),
            token_usage=usage,
        )
        self.db.add(summary_record)
        self.db.commit()
        self.db.refresh(summary_record)

        return summary_record

    def get_user_summaries(self, user_id: int) -> List[Summary]:
        stmt = select(Summary).where(Summary.user_id == user_id).order_by(Summary.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_user_summary(self, user_id: int, summary_id: int) -> Optional[Summary]:
        stmt = select(Summary).where(Summary.id == summary_id, Summary.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_user_summary(self, user_id: int, summary_id: int) -> bool:
        summary = self.get_user_summary(user_id, summary_id)
        if not summary:
            return False
        self.db.delete(summary)
        self.db.commit()
        return True
