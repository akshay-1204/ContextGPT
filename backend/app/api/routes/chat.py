"""RAG Chat and Conversation endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.chat import (
    ChatQuestionRequest,
    ChatAnswerResponse,
    ConversationCreate,
    ConversationResponse,
)
from backend.app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@router.post("/ask", response_model=ChatAnswerResponse)
def ask_rag_question(
    payload: ChatQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask a question grounded in user-owned document context using RAG.
    Returns the answer and verifiable source citations.
    """
    service = ChatService(db)
    try:
        result = service.ask_question(
            user_id=current_user.id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            source_id=payload.source_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat conversation session."""
    service = ChatService(db)
    conv = service.get_or_create_conversation(
        user_id=current_user.id,
        source_id=payload.source_id,
        initial_title=payload.title,
    )
    return conv


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chat conversations for the authenticated user."""
    service = ChatService(db)
    return service.get_user_conversations(current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full conversation history including user questions and assistant answers."""
    service = ChatService(db)
    conv = service.get_conversation_details(current_user.id, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation #{conversation_id} not found or you lack access permission.",
        )
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation thread and its associated message records."""
    service = ChatService(db)
    deleted = service.delete_conversation(current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation #{conversation_id} not found or you lack permission to delete it.",
        )
    return {"message": f"Conversation #{conversation_id} deleted successfully."}
