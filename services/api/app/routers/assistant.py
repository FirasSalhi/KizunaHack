"""FARMLINK voice assistant (ported from the Pilo Tech "Horizon" assistant, renamed).

POST /api/v1/assistant/chat answers one message of a conversation:
  - with the local Ollama model (same setup as Horizon: OLLAMA_HOST, OLLAMA_MODEL), given the farm data
    the dashboard is showing (weather, plots, irrigation advice, sensors) as context;
  - without Ollama, from that same data with simple rules, so the bubble always answers something true.
The answer is in the dashboard's language (fr, en, ar, ja) and short enough to be read aloud.
"""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
import uuid
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Literal

import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

Language = Literal["fr", "en", "ar", "ja"]
LANGUAGE_NAMES = {"fr": "français", "en": "English", "ar": "arabe tunisien (derja)", "ja": "日本語"}
LANGUAGE_RULE = {
    "fr": "Réponds en français.",
    "en": "Answer in English only, even if earlier messages were in another language.",
    "ar": "جاوب بالدارجة التونسية بالحروف العربية فقط.",
    "ja": "必ず日本語だけで答えてください。",
}
MAX_HISTORY = 12
MAX_CONVERSATIONS = 200


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    language: Language = "fr"
    conversation_id: str | None = Field(default=None, max_length=64)
    # What the dashboard shows right now (weather, plots, recommendation, alerts, sensors).
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    source: Literal["ollama", "rules"]
    assistant_name: str


LLM = Callable[[list[dict[str, str]]], str]


class LLMUnavailableError(RuntimeError):
    """Ollama is not running or the model is missing."""


def ollama_chat(messages: list[dict[str, str]]) -> str:
    """One answer from the local Ollama model (non-streaming)."""
    try:
        response = requests.post(
            f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 220, "num_ctx": 4096},
                "keep_alive": "10m",
            },
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LLMUnavailableError(str(exc)) from exc
    content = (response.json().get("message") or {}).get("content", "")
    # Some Qwen builds print their reasoning between <think> tags.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    if not content:
        raise LLMUnavailableError("empty answer")
    return content


def get_llm() -> LLM:
    return ollama_chat


def system_prompt(language: str, context: dict[str, Any]) -> str:
    name = settings.ASSISTANT_NAME
    return (
        f"Tu es {name}, l'assistant vocal de la plateforme agricole FARMLINK (Tunisie). "
        f"Réponds uniquement en {LANGUAGE_NAMES.get(language, 'français')}, en 1 à 3 phrases courtes, "
        "simples, pour un agriculteur, faciles à lire à voix haute (pas de listes, pas de Markdown). "
        "Utilise seulement les données de la ferme ci-dessous ; si une donnée manque, dis-le et indique "
        "la page du tableau de bord qui aide (Irrigation, Planification des cultures, Santé des plantes, "
        "Énergie solaire, Marché, Après-récolte). N'invente jamais de chiffres.\n"
        f"Données de la ferme (JSON) : {json.dumps(context, ensure_ascii=False)[:3000]}"
    )


# ---------------------------------------------------------------- rules (no Ollama)
def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


TEXTS: dict[str, dict[str, str]] = {
    "fr": {
        "hello": "Bonjour, je suis {name}. Demandez-moi quelle parcelle irriguer, la météo, le marché ou une maladie.",
        "weather": "Il fait {temp} °C, {sky}, vent {wind} km/h et humidité {hum} %.",
        "no_weather": "Je n'ai pas la météo pour le moment.",
        "market": "Les prix et les meilleurs mois pour vendre sont dans la page Marché.",
        "scan": "Prenez la plante en photo dans Santé des plantes : je vous dirai si elle semble malade.",
        "solar": "La page Énergie solaire montre comment la pompe continue au soleil pendant une coupure STEG.",
        "harvest": "Pour stocker votre récolte, ouvrez la page Après-récolte.",
        "plan": "Choisissez et validez vos cultures dans Planification des cultures.",
        "sensors": "Humidité du sol {soil} %, air {air} °C.",
        "no_sensors": "Le boîtier de terrain n'envoie pas de mesures en ce moment.",
        "unknown": "Je peux parler d'irrigation, de météo, du marché, des maladies, du solaire ou de la récolte.",
    },
    "en": {
        "hello": "Hello, I'm {name}. Ask me which plot to water, the weather, the market or a plant disease.",
        "weather": "It is {temp} °C, {sky}, wind {wind} km/h and humidity {hum} %.",
        "no_weather": "I don't have the weather right now.",
        "market": "Prices and the best months to sell are on the Market page.",
        "scan": "Take a photo in Plant health: I'll tell you if the plant looks sick.",
        "solar": "The Solar energy page shows how the pump keeps running on sunlight during a STEG outage.",
        "harvest": "To store your harvest, open the Post-Harvest page.",
        "plan": "Choose and validate your crops in Crop Planning.",
        "sensors": "Soil moisture {soil} %, air {air} °C.",
        "no_sensors": "The field unit is not sending readings right now.",
        "unknown": "I can talk about irrigation, weather, the market, diseases, solar energy or the harvest.",
    },
    "ar": {
        "hello": "عسلامة، أنا {name}. اسألني أما سانية نسقي، الطقس، السوق ولا مرض النبتة.",
        "weather": "الحرارة {temp} درجة، {sky}، الريح {wind} كم/س والرطوبة {hum} بالمية.",
        "no_weather": "ما عنديش الطقس توا.",
        "market": "الأسوام وأحسن شهور للبيع في صفحة السوق.",
        "scan": "صوّر النبتة في صحة النباتات ونقلك كان فيها مرض.",
        "solar": "صفحة الطاقة الشمسية تورّي كيفاش المضخة تكمّل بالشمس كي تقص الستاغ.",
        "harvest": "باش تخزن الصابة، حلّ صفحة ما بعد الحصاد.",
        "plan": "اختار وصادق على الزريعة في تخطيط الزراعة.",
        "sensors": "رطوبة التربة {soil} بالمية، الهواء {air} درجة.",
        "no_sensors": "وحدة الميدان ما تبعثش في قياسات توا.",
        "unknown": "نجم نحكي على السقي، الطقس، السوق، الأمراض، الطاقة الشمسية ولا الصابة.",
    },
    "ja": {
        "hello": "こんにちは、{name}です。水やりの圃場、天気、市場、病気について聞いてください。",
        "weather": "気温{temp}°C、{sky}、風{wind} km/h、湿度{hum}%です。",
        "no_weather": "今は天気を取得できません。",
        "market": "価格と売りどきは「市場」ページにあります。",
        "scan": "「植物の健康」で写真を撮ると、病気かどうかお知らせします。",
        "solar": "「太陽光エネルギー」ページで、停電中もポンプが動く様子を見られます。",
        "harvest": "収穫物の保管は「収穫後」ページを開いてください。",
        "plan": "「作物計画」で作物を選んで承認してください。",
        "sensors": "土壌水分{soil}%、気温{air}°Cです。",
        "no_sensors": "フィールドユニットから今は測定値が届いていません。",
        "unknown": "灌漑、天気、市場、病気、太陽光、収穫についてお答えできます。",
    },
}
INTENTS = [
    ("irrigation", r"irrig|arros|eau|water|سقي|ماء|مية|水|灌漑"),
    ("weather", r"meteo|temps|pluie|chaud|froid|weather|rain|طقس|مطر|حرارة|天気|雨"),
    ("sensors", r"capteur|sol|humidite|sensor|soil|حساس|تربة|رطوبة|センサー|土壌"),
    ("market", r"march|prix|vend|market|price|sell|سوق|سوم|بيع|市場|価格"),
    ("scan", r"malad|feuil|diagnos|photo|disease|leaf|sick|مرض|ورق|病気|葉"),
    ("solar", r"solaire|energie|steg|panneau|solar|energy|شمس|ستاغ|طاقة|太陽"),
    ("harvest", r"recolte|stock|harvest|storage|تخزين|صابة|収穫"),
    ("plan", r"plan|cultur|semer|crop|زرع|غراسة|作物|計画"),
    ("hello", r"bonjour|salut|hello|hi\b|عسلامة|سلام|こんにちは"),
]


def rule_answer(message: str, language: str, context: dict[str, Any]) -> str:
    t = TEXTS.get(language, TEXTS["fr"])
    said = _plain(message)
    intent = next((name for name, pattern in INTENTS if re.search(pattern, said)), "unknown")
    if intent == "irrigation":
        reco = context.get("recommendation") or {}
        text = " ".join(x for x in (reco.get("title"), reco.get("text")) if x)
        return text or t["plan"]
    if intent == "weather":
        w = context.get("weather") or {}
        if w.get("temperature_c") is None:
            return t["no_weather"]
        return t["weather"].format(
            temp=round(w["temperature_c"]),
            sky=w.get("sky", ""),
            wind=round(w.get("wind_kmh") or 0),
            hum=round(w.get("humidity_pct") or 0),
        )
    if intent == "sensors":
        s = context.get("sensors") or {}
        if s.get("soil_moisture") is None:
            return t["no_sensors"]
        return t["sensors"].format(soil=s["soil_moisture"], air=s.get("air_temp", "?"))
    if intent == "hello":
        return t["hello"].format(name=settings.ASSISTANT_NAME)
    return t[intent]


# ---------------------------------------------------------------- conversations (memory only)
_history: OrderedDict[str, tuple[float, list[dict[str, str]]]] = OrderedDict()
_lock = threading.Lock()


def _load(conversation_id: str | None) -> tuple[str, list[dict[str, str]]]:
    with _lock:
        if conversation_id and conversation_id in _history:
            _history.move_to_end(conversation_id)
            return conversation_id, list(_history[conversation_id][1])
    return uuid.uuid4().hex, []


def _save(conversation_id: str, messages: list[dict[str, str]]) -> None:
    with _lock:
        _history[conversation_id] = (time.time(), messages[-MAX_HISTORY:])
        _history.move_to_end(conversation_id)
        while len(_history) > MAX_CONVERSATIONS:
            _history.popitem(last=False)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, llm: LLM = Depends(get_llm)) -> ChatResponse:
    """Answer one message, in the dashboard's language, from the farm data it shows."""
    conversation_id, past = _load(request.conversation_id)
    messages = [{"role": "system", "content": system_prompt(request.language, request.context)}]
    messages += past + [{"role": "user", "content": request.message}]
    # Small models follow the conversation's language; restate the dashboard's language last.
    messages.append({"role": "system", "content": LANGUAGE_RULE[request.language]})
    try:
        answer = llm(messages)
        source: Literal["ollama", "rules"] = "ollama"
    except LLMUnavailableError:
        answer = rule_answer(request.message, request.language, request.context)
        source = "rules"
    _save(
        conversation_id,
        past
        + [{"role": "user", "content": request.message}, {"role": "assistant", "content": answer}],
    )
    return ChatResponse(
        message=answer,
        conversation_id=conversation_id,
        source=source,
        assistant_name=settings.ASSISTANT_NAME,
    )
