"""Conversational RAG service orchestrating question answering and grounded context."""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models.conversation import Conversation, Message
from backend.app.prompts.rag import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT_TEMPLATE, rag_prompt_template
from backend.app.services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.retrieval_service = RetrievalService(db)

    def get_or_create_conversation(
        self,
        user_id: int,
        conversation_id: Optional[int] = None,
        source_id: Optional[int] = None,
        initial_title: Optional[str] = None,
    ) -> Conversation:
        if conversation_id:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
            conv = self.db.execute(stmt).scalar_one_or_none()
            if conv:
                return conv

        # Create new conversation
        conv = Conversation(
            user_id=user_id,
            source_id=source_id,
            title=(initial_title or "New Conversation")[:255],
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def _call_rag_llm(self, prompt: str) -> str:
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
            logger.info("OPENAI_API_KEY missing; generating offline grounded answer.")
            return (
                "**[ContextGPT Offline Demonstration Mode]**\n\n"
                "*(Note: An active OPENAI_API_KEY is required for live generative responses)*\n\n"
                "I retrieved the relevant context passages from your source document. "
                "To synthesize answers and converse with full generative capabilities, "
                "please configure your OPENAI_API_KEY in the `.env` file."
            )

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url=base_url or None,
            )

            response = client.chat.completions.create(
                model=model,
                messages=[

                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"OpenAI RAG generation failed ({e}); falling back to grounded response.")
            return (
                "**[ContextGPT RAG Answer]**\n\n"
                f"*(Note: OpenAI API returned: {e})*\n\n"
                "I retrieved the relevant source sections from your document matching your query (see citations below). "
                "Once your OpenAI API key credits are active, live generative synthesis will be enabled."
            )


    def ask_question(
        self,
        user_id: int,
        question: str,
        conversation_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end RAG pipeline:
        1. Retrieval of user-owned chunks
        2. Context construction
        3. Grounded answer generation
        4. Storing user and assistant messages
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")

        # Ensure active conversation exists
        title_hint = clean_question[:40] + ("..." if len(clean_question) > 40 else "")
        conversation = self.get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            source_id=source_id,
            initial_title=title_hint,
        )

        # 1. Retrieve top chunks
        chunks = self.retrieval_service.retrieve_relevant_chunks(
            query=clean_question,
            user_id=user_id,
            source_id=source_id or conversation.source_id,
        )

        # 2. Build context
        if not chunks:
            answer = (
                "The provided source materials do not contain sufficient information to answer this question. "
                "No relevant document sections were found matching your query."
            )
            references = []
            is_grounded = False
        else:
            context_text, references = self.retrieval_service.construct_context(chunks)
            rag_prompt = rag_prompt_template.format(context=context_text, question=clean_question)
            answer = self._call_rag_llm(rag_prompt)
            is_grounded = True

        # 3. Persist messages in database
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=clean_question,
            source_references=None,
        )
        self.db.add(user_msg)
        self.db.flush()

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            source_references=references,
        )
        self.db.add(assistant_msg)
        self.db.commit()

        return {
            "conversation_id": conversation.id,
            "user_message_id": user_msg.id,
            "assistant_message_id": assistant_msg.id,
            "answer": answer,
            "source_references": references,
            "is_grounded": is_grounded,
        }

    def get_user_conversations(self, user_id: int) -> List[Conversation]:
        stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_conversation_details(self, user_id: int, conversation_id: int) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_conversation(self, user_id: int, conversation_id: int) -> bool:
        conv = self.get_conversation_details(user_id, conversation_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True
