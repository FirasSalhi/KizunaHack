"""Plant scanner API (app/routers/plants.py). The models are mocked: no download, no network."""

from collections.abc import AsyncGenerator, Iterator
from typing import Any

import httpx
import pytest

from app.api.deps import get_db_session
from app.main import app
from app.plants import engine

FAKE_RESULT: dict[str, Any] = {
    "engine": "verdant (110 houseplants)",
    "sure": True,
    "confidence": 0.82,
    "genus": {"name": None, "confidence": 0.82, "sure": False},
    "species": {
        "id": "mentha spicata",
        "common_name": "Spearmint",
        "scientific_name": "Mentha spicata",
    },
    "alternatives": [],
    "health": {"status": "unavailable", "message": "offline"},
}


class _NoDb:
    """Stands in for the database session: anonymous scans must never touch it."""

    def add(self, _obj: object) -> None:
        raise AssertionError("an anonymous scan must not be saved")


async def _no_db() -> AsyncGenerator[_NoDb, None]:
    yield _NoDb()


@pytest.fixture(autouse=True)
def _offline_db() -> Iterator[None]:
    app.dependency_overrides[get_db_session] = _no_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_status_reports_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: False)
    async with _client() as client:
        res = await client.get("/api/v1/plants/status")
    assert res.status_code == 200
    assert res.json()["installed"] is False
    assert set(res.json()["engines"]) == {"plantnet", "bioclip", "verdant"}


async def test_identify_without_models_says_how_to_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: False)
    async with _client() as client:
        res = await client.post("/api/v1/plants/identify", content=b"jpeg-bytes")
    assert res.status_code == 503
    assert res.json()["detail"]["error"]["code"] == "SCANNER_NOT_INSTALLED"


async def test_identify_needs_a_photo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: True)
    async with _client() as client:
        res = await client.post("/api/v1/plants/identify", content=b"")
    assert res.status_code == 422


async def test_identify_rejects_photos_over_10_mb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: True)
    async with _client() as client:
        res = await client.post("/api/v1/plants/identify", content=b"x" * (10 * 1024 * 1024 + 1))
    assert res.status_code == 413


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer demo_access_token_jwt"}])
async def test_visitors_and_demo_session_can_scan_but_nothing_is_saved(
    monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]
) -> None:
    monkeypatch.setattr(engine, "available", lambda: True)
    monkeypatch.setattr(engine, "identify", lambda data: dict(FAKE_RESULT))
    async with _client() as client:
        res = await client.post("/api/v1/plants/identify", content=b"jpeg-bytes", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["species"]["common_name"] == "Spearmint"
    assert body["saved"] is False
    assert "scan_id" not in body


async def test_unreadable_photo_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_data: bytes) -> dict[str, Any]:
        raise OSError("cannot identify image file")

    monkeypatch.setattr(engine, "available", lambda: True)
    monkeypatch.setattr(engine, "identify", broken)
    async with _client() as client:
        res = await client.post("/api/v1/plants/identify", content=b"not-an-image")
    assert res.status_code == 422
    assert res.json()["detail"]["error"]["code"] == "BAD_PHOTO"


async def test_history_needs_an_account() -> None:
    async with _client() as client:
        res = await client.get(
            "/api/v1/plants/scans", headers={"Authorization": "Bearer demo_access_token_jwt"}
        )
    assert res.status_code == 401


async def test_search_ignores_one_letter_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "available", lambda: False)  # not even reached
    async with _client() as client:
        res = await client.get("/api/v1/plants/search", params={"q": "a"})
    assert res.status_code == 200
    assert res.json() == []


def test_health_thresholds_match_is9ini() -> None:
    """Pl@ntNet diseases: >= 30 % sick, < 15 % healthy, in between uncertain (is9ini RAPPORT_IA)."""
    sick = engine._health_from_plantnet([{"name": "PHYTIN", "score": 0.64}])
    healthy = engine._health_from_plantnet([{"name": "XXXXXX", "score": 0.07}])
    unsure = engine._health_from_plantnet([{"name": "XXXXXX", "score": 0.2}])
    none_found = engine._health_from_plantnet([])
    assert sick["status"] == "possible_disease"
    assert healthy["status"] == "healthy_looking"
    assert unsure["status"] == "uncertain"
    assert none_found["status"] == "healthy_looking"


async def test_signed_in_scan_is_saved_with_its_photo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    import io
    import uuid

    from PIL import Image

    from app.api.deps import get_optional_user
    from app.core.config import settings
    from app.models.user import User

    saved: list[Any] = []

    class FakeDb:
        def add(self, obj: Any) -> None:
            obj.id = uuid.uuid4()
            saved.append(obj)

        async def commit(self) -> None:
            return None

    async def fake_db() -> AsyncGenerator[FakeDb, None]:
        yield FakeDb()

    user = User(id=uuid.uuid4(), email="sami@farmlink.tn", name="Sami", password_hash="x")
    app.dependency_overrides[get_db_session] = fake_db
    app.dependency_overrides[get_optional_user] = lambda: user
    monkeypatch.setattr(settings, "PLANT_SCANS_DIR", str(tmp_path))
    monkeypatch.setattr(engine, "available", lambda: True)
    monkeypatch.setattr(engine, "identify", lambda data: dict(FAKE_RESULT))
    photo = io.BytesIO()
    Image.new("RGB", (64, 48), "green").save(photo, "JPEG")
    try:
        async with _client() as client:
            res = await client.post("/api/v1/plants/identify", content=photo.getvalue())
    finally:
        app.dependency_overrides.pop(get_optional_user, None)

    assert res.status_code == 200
    body = res.json()
    assert body["saved"] is True
    assert len(saved) == 1 and saved[0].user_id == user.id
    assert saved[0].common_name == "Spearmint" and saved[0].health_status == "unavailable"
    assert body["scan_id"] == str(saved[0].id)
    assert (tmp_path / f"{saved[0].id}.jpg").exists()
    assert (tmp_path / f"{saved[0].id}_thumb.jpg").exists()
