import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
import httpx

from verifier import verify_receipt

app = FastAPI(title="Receipt Verifier")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.getenv("STORAGE_BUCKET", "receipts")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class VerifyRequest(BaseModel):
    payment_id: str
    # optional overrides
    account: str | None = None
    target_balance: float | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/verify")
async def verify(req: VerifyRequest, background_tasks: BackgroundTasks):
    # 1. Fetch payment row
    res = supabase.table("payments").select("*").eq("id", req.payment_id).single().execute()
    if not res.data:
        raise HTTPException(404, "payment not found")

    payment = res.data
    image_path = payment.get("image_path") or payment.get("receipt_path")
    if not image_path:
        raise HTTPException(400, "no image_path on payment")

    account = req.account or payment.get("account")
    target = req.target_balance or float(payment.get("target_amount", 0))

    if not account:
        raise HTTPException(400, "account missing")

    # 2. Download image from Storage
    try:
        # Prefer signed URL or direct download
        data = supabase.storage.from_(BUCKET).download(image_path)
    except Exception as e:
        raise HTTPException(400, f"failed to download image: {e}")

    # 3. Run verification
    success, reason = verify_receipt(data, account, target)

    status = "success" if success else "failed"

    # 4. Update payment
    supabase.table("payments").update({
        "status": status,
        "reason": reason,
        "verified_at": "now()",
    }).eq("id", req.payment_id).execute()

    return {"status": status, "reason": reason}