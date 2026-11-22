"""POST /api/v1/assistant/chat: Ollama answer, rule fallback, language and memory (no network)."""

from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import app
from app.routers.assistant import LLMUnavailableError, get_llm

CONTEXT = {
    "weather": {"temperature_c": 17.4, "sky": "ensoleillé", "wind_kmh": 12, "humidity_pct": 78},
    "recommendation": {"title": "Irriguer la parcelle Z2 (Olivier)", "text": "Déficit : 118 mm"},
    "sensors": {"soil_moisture": None},
}


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_ollama_answer_uses_farm_context_and_memory(client: httpx.AsyncClient) -> None:
    seen: list[list[dict[str, str]]] = []

    def llm(messages: list[dict[str, str]]) -> str:
        seen.append(messages)
        return "Arrosez Z2 aujourd'hui."

    app.dependency_overrides[get_llm] = lambda: llm
    try:
        first = await client.post(
            "/api/v1/assistant/chat",
            json={"message": "Quelle parcelle irriguer ?", "context": CONTEXT},
        )
        body = first.json()
        second = await client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "Et demain ?",
                "conversation_id": body["conversation_id"],
                "language": "en",
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert (
        first.status_code == 200
        and body["source"] == "ollama"
        and body["message"] == "Arrosez Z2 aujourd'hui."
    )
    assert "Z2 (Olivier)" in seen[0][0]["content"] and "français" in seen[0][0]["content"]
    assert "English" in seen[1][0]["content"]
    assert [m["role"] for m in seen[1][1:]] == [
        "user",
        "assistant",
        "user",
        "system",
    ]  # previous turn kept
    assert second.json()["conversation_id"] == body["conversation_id"]


async def test_without_ollama_rules_answer_from_the_dashboard_data(
    client: httpx.AsyncClient,
) -> None:
    def down(messages: list[dict[str, str]]) -> str:
        raise LLMUnavailableError("not running")

    app.dependency_overrides[get_llm] = lambda: down
    try:
        irrigation = await client.post(
            "/api/v1/assistant/chat", json={"message": "j'arrose quoi ?", "context": CONTEXT}
        )
        weather = await client.post(
            "/api/v1/assistant/chat",
            json={"message": "what's the weather?", "language": "en", "context": CONTEXT},
        )
        sensors = await client.post(
            "/api/v1/assistant/chat", json={"message": "humidité du sol", "context": CONTEXT}
        )
    finally:
        app.dependency_overrides.clear()
    assert irrigation.json()["source"] == "rules"
    assert irrigation.json()["message"] == "Irriguer la parcelle Z2 (Olivier) Déficit : 118 mm"
    assert weather.json()["message"].startswith("It is 17 °C")
    assert "n'envoie pas" in sensors.json()["message"]


async def test_empty_message_is_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/assistant/chat", json={"message": ""})
    assert r.status_code == 422
