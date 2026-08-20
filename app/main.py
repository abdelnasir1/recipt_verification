import logging
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from .config import settings
from .celery_app import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Receipt verification"
)

# Request/Response Models
class VerifyByUrlRequest(BaseModel):
    """Receipt image path and payment row identifier."""
    model_config = ConfigDict(extra="forbid")

    image_url: str = Field(..., min_length=1, description="Path to image in Supabase storage")
    payment_id: str = Field(..., min_length=1, description="Payment record ID")

@app.post("/verify/storage", status_code=200, response_model=None)
async def verify_with_storage_url(request: VerifyByUrlRequest) -> Response:
    """
    Queue receipt verification and return without waiting for OCR.
    """
    try:
        celery_app.send_task(
            "app.tasks.verify_receipt_task",
            args=[request.image_url, request.payment_id],
        )
        logger.info("Queued receipt verification for payment %s", request.payment_id)
        return Response(status_code=200)
    except Exception as e:
        logger.error("Failed to queue receipt verification: %s", e, exc_info=True)
        raise HTTPException(503, "Receipt verification queue is unavailable") from e