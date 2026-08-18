import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client, Client
from typing import Optional

from .config import settings
from .verifier import verify_receipt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate configuration
try:
    settings.validate()
except RuntimeError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Initialize FastAPI
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Receipt verification service for Dokploy"
)

# Initialize Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# Request/Response Models
class VerifyByUrlRequest(BaseModel):
    """Verification using image URL from Supabase Storage"""
    image_path: str = Field(..., description="Path to image in Supabase storage")
    account_number: str = Field(..., description="Account number to verify")
    amount: float = Field(..., description="Expected amount")
    payment_id: Optional[str] = Field(None, description="Optional payment record ID for database update")

class VerificationResponse(BaseModel):
    """Standardized verification response"""
    status: str = Field(..., description="'success' or 'failed'")
    verified: bool = Field(..., description="Verification result")
    reason: str = Field(..., description="Reason if failed, empty if success")
    amount: float = Field(..., description="Amount verified")
    account: str = Field(..., description="Account verified")
    timestamp: str = Field(..., description="ISO timestamp of verification")
    payment_id: Optional[str] = Field(None, description="Payment ID if provided")

@app.post("/verify/storage", response_model=VerificationResponse)
async def verify_with_storage_url(request: VerifyByUrlRequest):
    """
    Verify receipt using image from Supabase Storage
    
    Args:
        request: Contains storage path, account number, amount, and optional payment_id
    
    Returns:
        VerificationResponse with status, reason, and verification details
    """
    try:
        logger.info(f"Downloading image from storage: {request.image_path}")

        # Download image from Supabase Storage
        try:
            image_bytes = supabase.storage.from_(settings.storage_bucket).download(request.image_path)
        except Exception as e:
            logger.error(f"Failed to download image from storage: {e}")
            raise HTTPException(400, f"Failed to download image from storage: {e}")

        logger.info(f"Verifying receipt for account {request.account_number}, amount {request.amount}")

        # Run verification
        success, reason = verify_receipt(
            image_bytes,
            request.account_number,
            request.amount,
            ssim_threshold=settings.ssim_threshold
        )

        status = "success" if success else "failed"
        timestamp = datetime.utcnow().isoformat()

        response = VerificationResponse(
            status=status,
            verified=success,
            reason=reason,
            amount=request.amount,
            account=request.account_number,
            timestamp=timestamp,
            payment_id=request.payment_id
        )

        # Update database if payment_id provided and UPDATE_DATABASE is enabled
        if request.payment_id and os.getenv("UPDATE_DATABASE", "true").lower() == "true":
            try:
                table_name = os.getenv("DATABASE_TABLE", "payments")
                supabase.table(table_name).update({
                    "status": status,
                    "reason": reason,
                    "verified_at": timestamp,
                }).eq("id", request.payment_id).execute()
                logger.info(f"Updated database record {request.payment_id} with status {status}")
            except Exception as e:
                logger.error(f"Failed to update database: {e}")
                # Don't fail the response if database update fails

        logger.info(f"Verification complete: {status} - {reason if reason else 'Receipt valid'}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification error: {e}", exc_info=True)
        raise HTTPException(500, f"Verification failed: {str(e)}")