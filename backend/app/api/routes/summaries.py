"""Summarization API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.summary import SummaryCreate, SummaryResponse
from backend.app.services.summary_service import SummaryService

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.post("", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
def create_summary(
    payload: SummaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a summary for an existing processed source document."""
    service = SummaryService(db)
    try:
        summary = service.summarize_source(
            user_id=current_user.id,
            source_id=payload.source_id,
            summary_type=payload.summary_type,
            custom_instructions=payload.custom_instructions,
            title=payload.title,
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("", response_model=List[SummaryResponse])
def list_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all summaries created by the authenticated user."""
    service = SummaryService(db)
    return service.get_user_summaries(current_user.id)


@router.get("/{summary_id}", response_model=SummaryResponse)
def get_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details and full text of a specific summary."""
    service = SummaryService(db)
    summary = service.get_user_summary(current_user.id, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary #{summary_id} not found or you lack permission to view it.",
        )
    return summary


@router.delete("/{summary_id}", status_code=status.HTTP_200_OK)
def delete_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved summary."""
    service = SummaryService(db)
    deleted = service.delete_user_summary(current_user.id, summary_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary #{summary_id} not found or you lack permission to delete it.",
        )
    return {"message": f"Summary #{summary_id} deleted successfully."}
