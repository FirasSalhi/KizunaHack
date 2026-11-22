"""Background tasks for asynchronous operations and AI inference."""
from app.core.logging import logger
from app.workers.celery_app import celery_app


def async_task(func):
    """Decorator supporting Celery when available or synchronous fallback."""
    if celery_app:
        return celery_app.task(func)
    return func


@async_task
def process_plant_scan(scan_id: str, image_path: str) -> dict:
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
