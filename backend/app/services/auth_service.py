"""Authentication and User Management Service."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from backend.app.db.models.user import User
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.schemas.user import UserRegister, TokenResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def register_user(self, payload: UserRegister) -> User:
        clean_email = payload.email.lower().strip()
        existing = self.get_user_by_email(clean_email)
        if existing:
            raise ValueError(f"An account with email '{clean_email}' already exists.")

        user = User(
            name=payload.name.strip(),
            email=clean_email,
            password_hash=hash_password(payload.password),
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_token_pair(self, user: User) -> TokenResponse:
        # Access token
        access_token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "name": user.name},
        )

        # Refresh token
        raw_refresh_token = generate_refresh_token()
        token_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(db_refresh)
        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh_access_token(self, raw_refresh_token: str) -> TokenResponse:
        token_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        record = self.db.execute(stmt).scalar_one_or_none()

        if not record:
            raise ValueError("Invalid refresh token.")

        if record.is_revoked:
            raise ValueError("Refresh token has been revoked.")

        now_utc = datetime.now(timezone.utc)
        record_exp = record.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)

        if record_exp < now_utc:
            raise ValueError("Refresh token has expired.")

        user = self.get_user_by_id(record.user_id)
        if not user or not user.is_active:
            raise ValueError("User account is inactive or disabled.")

        # Refresh Token Rotation: Revoke previous token and create new pair
        record.is_revoked = True
        new_refresh_token = generate_refresh_token()
        new_token_hash = hash_token(new_refresh_token)
        record.replaced_by = new_token_hash

        new_expires_at = now_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            is_revoked=False,
        )
        self.db.add(new_record)
        self.db.commit()

        new_access_token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "name": user.name},
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def revoke_refresh_token(self, raw_refresh_token: str) -> bool:
        token_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        record = self.db.execute(stmt).scalar_one_or_none()
        if record and not record.is_revoked:
            record.is_revoked = True
            self.db.commit()
            return True
        return False
