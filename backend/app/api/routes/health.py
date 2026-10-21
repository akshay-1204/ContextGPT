"""Health and Readiness probe routes."""

from fastapi import APIRouter, status, Response
from backend.app.core.config import settings
from backend.app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: verifies that the application server is responsive."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@router.get("/health/ready")
def readiness_check(response: Response):
    """Readiness probe: validates database connectivity."""
    db_connected = check_db_connection()
    if not db_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "message": "Database ping failed",
        }
    return {
        "status": "ready",
        "database": "connected",
    }
