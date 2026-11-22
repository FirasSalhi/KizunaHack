from datetime import timedelta
import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hashing() -> None:
    raw = "SuperSecretPassword123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_token_creation_and_decoding() -> None:
    user_id = "018f3a22-4a7b-7000-8000-000000000001"
    token = create_access_token(subject=user_id)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_expired_access_token() -> None:
    user_id = "018f3a22-4a7b-7000-8000-000000000001"
    # Token that expired 10 minutes ago
    token = create_access_token(subject=user_id, expires_delta=timedelta(minutes=-10))
    payload = decode_access_token(token)
    assert payload is None


def test_refresh_token_hashing() -> None:
    raw, hashed = create_refresh_token()
    assert len(raw) > 20
    assert len(hashed) == 64
    assert hash_refresh_token(raw) == hashed
