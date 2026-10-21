"""Security, Passlib Bcrypt Hashing, Python-Jose JWT, and Base64 Utilities."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import settings

# Passlib CryptContext configured with bcrypt (primary) and argon2 (fallback/compatibility)
pwd_context = CryptContext(schemes=["bcrypt", "argon2"], deprecated="auto")


# ==============================================================================
# Base64 Utility Functions
# ==============================================================================

def base64_encode(data: Union[str, bytes]) -> str:
    """Encode a string or bytes to URL-safe base64 string without trailing padding."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def base64_decode(data: str) -> str:
    """Decode a URL-safe base64 string back to UTF-8 text."""
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding).decode("utf-8")


# ==============================================================================
# Password Hashing & Verification (Passlib [bcrypt])
# ==============================================================================

def hash_password(password: str) -> str:
    """Hash a plain text password using passlib bcrypt."""
    try:
        return pwd_context.hash(password)
    except Exception:
        # Direct bcrypt fallback if passlib backend inspection encounters issues
        try:
            import bcrypt
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except Exception:
            # PBKDF2 secure fallback
            salt = secrets.token_hex(16)
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
            return f"pbkdf2:sha256:{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password using passlib bcrypt."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        try:
            import bcrypt
            if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            pass

        # Check for PBKDF2 fallback format
        try:
            parts = hashed_password.split(":")
            if len(parts) == 4 and parts[0] == "pbkdf2" and parts[1] == "sha256":
                salt = parts[2]
                key = parts[3]
                new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
                return secrets.compare_digest(new_key.hex(), key)
        except Exception:
            pass

        return False


# ==============================================================================
# JWT Access Token Management (Python-Jose)
# ==============================================================================

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token using python-jose (valid for 1 hour by default)."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token using python-jose."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except (JWTError, Exception):
        return None


# ==============================================================================
# Refresh Token & Token Hashing (Base64)
# ==============================================================================

def generate_refresh_token() -> str:
    """Generate a high-entropy cryptographically random refresh token string using base64."""
    random_bytes = secrets.token_bytes(48)
    return base64_encode(random_bytes)


def hash_token(token: str) -> str:
    """Hash token with SHA-256 before storing in database for rotation/revocation security."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
