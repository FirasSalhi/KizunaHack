import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.schemas.auth import FarmMembershipResponse, MeResponse, TokenResponse


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json() == {"ok": True}


@pytest.mark.asyncio
async def test_signup_endpoint() -> None:
    test_user_id = uuid.uuid4()
    mock_user = User(
        id=test_user_id,
        email="sami@farmlink.tn",
        name="Sami Ben Ali",
        password_hash="hashed",
        locale="fr",
    )
    mock_tokens = TokenResponse(
        access_token="test_access_jwt_token",
        refresh_token="test_refresh_token_value",
        token_type="bearer",
        expires_in=86400,
    )

    with patch("app.api.v1.endpoints.auth.AuthService") as mock_service_cls:
        service_instance = mock_service_cls.return_value
        service_instance.register = AsyncMock(return_value=(mock_user, mock_tokens))

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "name": "Sami Ben Ali",
                "email": "sami@farmlink.tn",
                "password": "FarmPassword2026!",
                "farm_name": "El Mornag Vineyard",
                "locale": "fr",
            }
            res = await client.post("/api/v1/auth/signup", json=payload)
            assert res.status_code == 201
            data = res.json()
            assert data["access_token"] == "test_access_jwt_token"
            assert data["refresh_token"] == "test_refresh_token_value"
            assert "fl_access" in res.cookies


@pytest.mark.asyncio
async def test_login_endpoint() -> None:
    test_user_id = uuid.uuid4()
    mock_user = User(
        id=test_user_id,
        email="sami@farmlink.tn",
        name="Sami Ben Ali",
        password_hash="hashed",
        locale="fr",
    )
    mock_tokens = TokenResponse(
        access_token="test_access_jwt_token",
        refresh_token="test_refresh_token_value",
        token_type="bearer",
        expires_in=86400,
    )

    with patch("app.api.v1.endpoints.auth.AuthService") as mock_service_cls:
        service_instance = mock_service_cls.return_value
        service_instance.login = AsyncMock(return_value=(mock_user, mock_tokens))

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "email": "sami@farmlink.tn",
                "password": "FarmPassword2026!",
            }
            res = await client.post("/api/v1/auth/login", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["access_token"] == "test_access_jwt_token"
            assert "fl_access" in res.cookies


@pytest.mark.asyncio
async def test_me_endpoint() -> None:
    test_user_id = uuid.uuid4()
    mock_user = User(
        id=test_user_id,
        email="sami@farmlink.tn",
        name="Sami Ben Ali",
        password_hash="hashed",
        locale="fr",
    )
    mock_me = MeResponse(
        id=test_user_id,
        email="sami@farmlink.tn",
        name="Sami Ben Ali",
        locale="fr",
        memberships=[
            FarmMembershipResponse(
                farm_id=uuid.uuid4(),
                farm_name="El Mornag Vineyard",
                role="owner",
            )
        ],
    )

    token = create_access_token(subject=str(test_user_id))

    with (
        patch("app.api.deps.UserRepository") as mock_repo_cls,
        patch("app.api.v1.endpoints.users.AuthService") as mock_auth_cls,
    ):
        user_repo = mock_repo_cls.return_value
        user_repo.get_by_id = AsyncMock(return_value=mock_user)

        auth_service = mock_auth_cls.return_value
        auth_service.get_me = AsyncMock(return_value=mock_me)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["email"] == "sami@farmlink.tn"
            assert data["name"] == "Sami Ben Ali"
            assert len(data["memberships"]) == 1
            assert data["memberships"][0]["farm_name"] == "El Mornag Vineyard"
