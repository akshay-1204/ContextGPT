"""User profile routes."""

from fastapi import APIRouter, Depends
from backend.app.api.dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated user details."""
    return current_user
