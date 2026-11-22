"""Celery application configuration for background job execution."""

from app.core.config import settings

# Graceful loading so the application operates seamlessly with or without celery installed
try:
    from celery import Celery  # type: ignore

    celery_app = Celery(
        "farmlink_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["app.workers.tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
except ImportError:
    celery_app = None
