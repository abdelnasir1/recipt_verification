#!/usr/bin/env python3
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Paddle's PIR runtime currently cannot convert an attribute used by this OCR model.
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")

import cv2
import numpy as np
from paddleocr import PaddleOCR
from rapidfuzz import fuzz
from skimage.metrics import structural_similarity as ssim

from .config import settings

# Load reference receipt once at startup
REFERENCE_PATH = settings.reference_image
REFERENCE_SIZE = settings.reference_size

def load_reference() -> np.ndarray:
    img = cv2.imread(REFERENCE_PATH, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Reference image not found: {REFERENCE_PATH}")
    img = cv2.resize(img, REFERENCE_SIZE, interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (5, 5), 0)
    return img

REF_IMG = load_reference()

# Initialize PaddleOCR - removed deprecated parameters
ocr = PaddleOCR(
    text_recognition_model_name="arabic_PP-OCRv3_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    lang='en',
    ocr_version="PP-OCRv4"
)

def find_after(label: str, lines: list[str], threshold: int = 85) -> Optional[str]:
    for i, line in enumerate(lines):
        if fuzz.ratio(label.lower(), line.lower()) > threshold:
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return None

def is_in_last_week(date_str: str) -> bool:
    # Try several common formats
    formats = [
        "%d-%b-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
    ]
    date_obj = None
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str.strip(), fmt)
            break
        except ValueError:
            continue
    if date_obj is None:
        return False

    now = datetime.now()
    return (now - timedelta(days=7)) <= date_obj <= now

def parse_amount(raw: str) -> Optional[float]:
    # Remove currency symbols and commas
    cleaned = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None

def verify_receipt(
    image_bytes: bytes,
    expected_account: str,
    target_balance: float,
    ssim_threshold: float = 0.65,
) -> Tuple[bool, str]:
    """
    Returns (success: bool, reason: str)
    """
    # Decode the uploaded image once and keep the original color image for OCR.
    nparr = np.frombuffer(image_bytes, np.uint8)
    original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if original_img is None:
        return False, "invalid image"

    # SSIM uses a normalized grayscale copy and must not change the OCR input.
    ssim_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    ssim_img = cv2.resize(ssim_img, REFERENCE_SIZE, interpolation=cv2.INTER_AREA)
    ssim_img = cv2.GaussianBlur(ssim_img, (5, 5), 0)

    score = ssim(REF_IMG, ssim_img)
    if score < ssim_threshold:
        return False, f"image quality too low or not a receipt (ssim={score:.3f})"

    # OCR (cls parameter removed - no longer supported)
    result = ocr.predict(original_img)
  
    if not result :
        return False, "OCR failed – no text found"

    lines = [line for line in result[0].get("rec_texts",[])]
    print(lines)

    date = find_after("Date & Time", lines) or find_after("Date", lines)
    if not date:
        return False, "can't find date"
    if not is_in_last_week(date):
        return False, "transaction older than one week"

    to_acc = find_after("To Account", lines) or find_after("To", lines)
    if not to_acc:
        return False, "can't find To Account"
    if to_acc.replace(" ", "") != expected_account.replace(" ", ""):
        return False, "another account"

    amount_raw = find_after("Amount", lines)
    if not amount_raw:
        return False, "can't find Amount"
    amount = parse_amount(amount_raw)
    if amount is None:
        return False, "invalid amount format"
    if amount < target_balance:
        return False, "not enough amount"

    return True, ""