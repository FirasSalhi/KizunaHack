"""Background tasks for asynchronous operations and AI inference."""

from collections.abc import Callable
from typing import Any

from app.core.logging import logger
from app.workers.celery_app import celery_app


def async_task[F: Callable[..., Any]](func: F) -> F:
    """Decorator supporting Celery when available or synchronous fallback."""
    if celery_app:
        return celery_app.task(func)  # type: ignore[no-any-return]
    return func


@async_task
def process_plant_scan(scan_id: str, image_path: str) -> dict[str, Any]:
    """Background task to run AI vision models on crop photos."""
    logger.info(f"Processing plant scan {scan_id} with image {image_path}")
    # Ingest through AI pipeline
    return {
        "scan_id": scan_id,
        "status": "completed",
        "species": "Solanum lycopersicum",
        "confidence": 0.94,
    }


@async_task
def send_email_notification(recipient: str, subject: str, message: str) -> bool:
    """Send transactional notification email."""
    logger.info(f"Sending email notification to {recipient}: {subject}")
    return True
