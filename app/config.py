import os
class Settings:

    # Supabase Configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    storage_bucket: str = os.getenv("STORAGE_BUCKET", "receipts")
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    expected_account_number: str = os.getenv("ACCOUNT_NUMBER", "")
    expected_amount: float = float(os.getenv("AMOUNT", "0"))

    # OCR Configuration
    reference_image: str = os.getenv("REFERENCE_IMAGE", "reference_receipt.jpg")
    reference_size: tuple = (225  ,225)
    ocr_lang: str = os.getenv("OCR_LANGUAGE", "en")  # "ar" for Arabic, "en" for English
    use_gpu: bool = os.getenv("USE_GPU", "false").lower() == "true"

    # Verification Thresholds
    ssim_threshold: float = float(os.getenv("SSIM_THRESHOLD", "0.65"))
    fuzzy_match_threshold: int = int(os.getenv("FUZZY_MATCH_THRESHOLD", "85"))

    # FastAPI Configuration
    app_title: str = "Receipt Verifier"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server Configuration
    workers: int = int(os.getenv("WORKERS", "1"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


    def __repr__(self) -> str:
        """String representation (redacts sensitive data)"""
        return (
            f"Settings(supabase_url={'***' if self.supabase_url else 'missing'}, "
            f"storage_bucket={self.storage_bucket}, "
            f"ocr_lang={self.ocr_lang}, "
            f"use_gpu={self.use_gpu})"
        )

settings = Settings()
