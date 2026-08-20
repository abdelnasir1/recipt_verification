import logging
import os
from datetime import datetime
from urllib.parse import unquote, urlparse

from supabase import Client, create_client

from .celery_app import celery_app
from .config import settings
from .verifier import verify_receipt

logger = logging.getLogger(__name__)


def _supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)


def _storage_path(image_url: str) -> str:
    """Return a Supabase Storage object path from a path or public URL."""
    parsed = urlparse(image_url)
    if not parsed.scheme or not parsed.netloc:
        return image_url.lstrip("/")

    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    marker = ["storage", "v1", "object", "public"]
    try:
        marker_index = next(
            index for index in range(len(path_parts) - len(marker) + 1)
            if path_parts[index:index + len(marker)] == marker
        )
    except StopIteration as exc:
        raise ValueError("image_url is not a Supabase public storage URL") from exc

    bucket_index = marker_index + len(marker)
    if bucket_index >= len(path_parts):
        raise ValueError("image_url does not contain a storage bucket")
    bucket = path_parts[bucket_index]
    if bucket != settings.storage_bucket:
        raise ValueError(f"image_url bucket must be {settings.storage_bucket}")

    object_path = "/".join(path_parts[bucket_index + 1:])
    if not object_path:
        raise ValueError("image_url does not contain an image path")
    return object_path


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
        image_path = _storage_path(image_url)
        logger.info("Downloading receipt image from storage path %s", image_path)
        image_bytes = _supabase().storage.from_(settings.storage_bucket).download(image_path)
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