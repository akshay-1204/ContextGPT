"""Prompt templates for Summarization and RAG."""

from backend.app.prompts.summarization import get_summarization_prompt, get_chunk_summary_prompt, COMBINE_SUMMARIES_PROMPT
from backend.app.prompts.rag import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT_TEMPLATE

__all__ = [
    "get_summarization_prompt",
    "get_chunk_summary_prompt",
    "COMBINE_SUMMARIES_PROMPT",
    "RAG_SYSTEM_PROMPT",
    "RAG_USER_PROMPT_TEMPLATE",
]
