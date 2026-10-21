"""Source ingestion and management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.source import (
    SourceResponse,
    WebpageSourceCreate,
    APISourceCreate,
    URLSourceCreate,
    DatabaseSourceCreate,
    YouTubeSourceCreate,
)

from backend.app.services.source_service import SourceService

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.post("/upload", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and process document files (PDF, TXT, CSV, DOCX, XLSX, JSON, XML, Images)."""
    service = SourceService(db)
    try:
        source = await service.handle_file_upload(
            user_id=current_user.id,
            file=file,
            title=title,
        )
        return source
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File processing error: {str(e)}")


@router.post("/webpage", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_webpage_source(
    payload: WebpageSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest and extract content from an HTTP or HTTPS webpage URL with SSRF safeguards."""
    service = SourceService(db)
    source = service.process_and_save_source(
        user_id=current_user.id,
        source_type="webpage",
        source_reference=payload.url,
        title=payload.title or payload.url,
    )
    return source


@router.post("/api", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_api_source(
    payload: APISourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest structured data from an external REST API endpoint with SSRF protections."""
    service = SourceService(db)
    source = service.process_and_save_source(
        user_id=current_user.id,
        source_type="api",
        source_reference=payload.endpoint_url,
        title=payload.title or payload.endpoint_url,
        initial_metadata={"headers": payload.headers},
    )
    return source


@router.post("/url", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_url_source(
    payload: URLSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest content from any user-provided URL (JSON API, webpage, plain text) with auto-detection."""
    service = SourceService(db)
    source = service.process_and_save_source(
        user_id=current_user.id,
        source_type="url",
        source_reference=payload.url,
        title=payload.title or payload.url,
        initial_metadata={"headers": payload.headers} if payload.headers else None,
    )
    return source

@router.post("/database", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_database_source(
    payload: DatabaseSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest structured rows from an authorized read-only database query."""
    service = SourceService(db)
    source = service.process_and_save_source(
        user_id=current_user.id,
        source_type="database",
        source_reference=payload.connection_string,
        title=payload.title or "Database Query Source",
        initial_metadata={"query": payload.query},
    )
    return source


@router.post("/youtube", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_youtube_source(
    payload: YouTubeSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest, fetch transcripts, and index a YouTube video for AI summarization."""
    service = SourceService(db)
    source = service.process_and_save_source(
        user_id=current_user.id,
        source_type="youtube",
        source_reference=payload.url,
        title=payload.title or "YouTube Video",
    )
    return source



@router.get("", response_model=List[SourceResponse])
def list_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sources owned by the authenticated user."""
    service = SourceService(db)
    return service.get_user_sources(current_user.id)


@router.get("/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details and processing status of a specific source."""
    service = SourceService(db)
    source = service.get_user_source(current_user.id, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source #{source_id} not found or you lack permission to access it.",
        )
    return source


@router.delete("/{source_id}", status_code=status.HTTP_200_OK)
def delete_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a source and all associated document chunks and summaries."""
    service = SourceService(db)
    deleted = service.delete_user_source(current_user.id, source_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source #{source_id} not found or you lack permission to delete it.",
        )
    return {"message": f"Source #{source_id} deleted successfully."}
