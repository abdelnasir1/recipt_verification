import logging
import os
from datetime import datetime

from supabase import Client, create_client

from .celery_app import celery_app
from .config import settings
from .verifier import verify_receipt

logger = logging.getLogger(__name__)


def _supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)


def _update_payment(payment_id: str, status: str, reason: str, timestamp: str) -> None:
    _supabase().table(os.getenv("DATABASE_TABLE", "payments")).update({
        "status": status,
        "reason": reason,
        "verified_at": timestamp,
    }).eq("id", payment_id).execute()


@celery_app.task(
    bind=True,
    name="app.tasks.verify_receipt_task",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def verify_receipt_task(self, image_url: str, payment_id: str) -> None:
    timestamp = datetime.utcnow().isoformat()
    try:
        image_bytes = _supabase().storage.from_(settings.storage_bucket).download(image_url)
        success, reason = verify_receipt(
            image_bytes,
            settings.expected_account_number,
            settings.expected_amount,
            ssim_threshold=settings.ssim_threshold,
        )
        status = "success" if success else "failed"
    except Exception as exc:
        status = "failed"
        reason = f"verification error: {exc}"
        logger.exception("Receipt verification failed for payment %s", payment_id)

    try:
        _update_payment(payment_id, status, reason, timestamp)
        logger.info("Updated payment %s with status %s", payment_id, status)
    except Exception:
        logger.exception("Failed to update payment %s", payment_id)
        raise