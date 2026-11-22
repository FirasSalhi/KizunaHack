from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FARMLINK API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database connection URL (PostgreSQL with asyncpg, or SQLite async fallback)
    DATABASE_URL: str = "postgresql+asyncpg://farmlink:farmlink@localhost:5433/farmlink"

    # JWT Authentication
    SECRET_KEY: str = "farmlink_super_secure_jwt_secret_key_change_in_production_32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis Broker & Celery Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS settings
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://farmlink.localhost",
        # Static irrigation demo pages (research/irrigation-notebook/html)
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # Plant scanner (app/plants, ported from is9ini)
    # Free Pl@ntNet key from https://my.plantnet.org (500 photos/day); empty = offline engines only
    PLANTNET_API_KEY: str = ""
    # auto (Pl@ntNet -> BioCLIP 2 -> verdant) | plantnet | bioclip | verdant
    PLANT_ENGINE: str = "auto"
    # Models and databases (python -m app.plants.catalog) and saved scan photos
    PLANT_MODELS_DIR: str = str(Path(__file__).resolve().parents[2] / "models" / "plants")
    PLANT_SCANS_DIR: str = str(Path(__file__).resolve().parents[2] / "data" / "plant_scans")

    # Field-unit sensor feed (firmware/field-unit -> LoRa gateway -> HiveMQ, see firmware/README.md)
    SENSOR_FEED_ENABLED: bool = True
    SENSOR_MQTT_HOST: str = "broker.hivemq.com"
    SENSOR_MQTT_PORT: int = 8883
    SENSOR_MQTT_USERNAME: str = ""  # only for a private HiveMQ Cloud cluster
    SENSOR_MQTT_PASSWORD: str = ""
    SENSOR_TOPIC_PREFIX: str = "farmlink/v2"
    # Devices shown on the dashboard. The public broker is open to anyone, so only these are kept.
    # An empty list keeps every device on the topic.
    SENSOR_DEVICE_IDS: list[str] = ["kizunahack-field-unit-1"]

    # Voice assistant (app/routers/assistant.py), ported from the Pilo Tech "Horizon" assistant.
    # Local Ollama model; without Ollama the assistant still answers from the farm's data (rules).
    ASSISTANT_NAME: str = "Mdhalla"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # Security & Cookie Flags
    COOKIE_SECURE: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
