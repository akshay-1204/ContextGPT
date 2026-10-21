"""Tests for Authentication, Passlib Bcrypt hashing, Python-Jose JWT tokens, and Base64."""

from fastapi.testclient import TestClient
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    base64_encode,
    base64_decode,
)


def test_user_registration(client: TestClient):
    payload = {
        "name": "Grace Hopper",
        "email": "grace@example.com",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "grace@example.com"
    assert data["name"] == "Grace Hopper"
    assert "password_hash" not in data  # Never expose password hash in response


def test_duplicate_email_registration_fails(client: TestClient):
    payload = {
        "name": "Grace Hopper",
        "email": "grace_dup@example.com",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_password_mismatch_fails(client: TestClient):
    payload = {
        "name": "Grace Hopper",
        "email": "mismatch@example.com",
        "password": "Password1!",
        "password_confirm": "Password2!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_login_and_token_refresh(client: TestClient):
    # 1. Register
    reg_payload = {
        "name": "Alan Turing",
        "email": "alan@example.com",
        "password": "EnigmaPassword123!",
        "password_confirm": "EnigmaPassword123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_res = client.post("/api/v1/auth/login", json={"email": "alan@example.com", "password": "EnigmaPassword123!"})
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    # Verify 1 hour token expiration (3600 seconds)
    assert tokens["expires_in"] == 3600

    # 3. Access protected /auth/me
    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alan@example.com"

    # 4. Rotate refresh token
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["expires_in"] == 3600

    # 5. Verify old refresh token is now revoked
    old_reuse_res = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert old_reuse_res.status_code == 401


def test_login_invalid_password(client: TestClient):
    reg_payload = {
        "name": "Test User",
        "email": "testwrong@example.com",
        "password": "CorrectPassword1!",
        "password_confirm": "CorrectPassword1!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post("/api/v1/auth/login", json={"email": "testwrong@example.com", "password": "WrongPassword!"})
    assert login_res.status_code == 401


def test_unauthenticated_request_fails(client: TestClient):
    response = client.get("/api/v1/sources")
    assert response.status_code == 401


def test_passlib_bcrypt_and_jose_security():
    # Passlib bcrypt hashing
    raw_pwd = "SuperSecretPassword99!"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

    # Jose JWT creation and decode (valid for 1 hour)
    token = create_access_token(subject=42, extra_claims={"email": "dev@example.com"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "dev@example.com"
    # Token expiration should be roughly 3600 seconds from issued-at
    assert payload["exp"] - payload["iat"] == 3600


def test_base64_utilities():
    original_text = "ContextGPT-Base64-Authentication-Test-String"
    encoded = base64_encode(original_text)
    assert isinstance(encoded, str)
    assert encoded != original_text
    decoded = base64_decode(encoded)
    assert decoded == original_text
