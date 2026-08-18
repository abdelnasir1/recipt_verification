#!/usr/bin/env python3
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

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
    use_angle_cls=False,
    lang=settings.ocr_lang,
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
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False, "invalid image"

    img = cv2.resize(img, REFERENCE_SIZE, interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (5, 5), 0)

    score = ssim(REF_IMG, img)
    if score < ssim_threshold:
        return False, f"image quality too low or not a receipt (ssim={score:.3f})"

    # OCR
    result = ocr.ocr(image_bytes)
    if not result or not result[0]:
        return False, "OCR failed – no text found"

    lines = [line[1][0] for line in result[0]]

    trx = find_after("Trx. ID", lines) or find_after("Transaction ID", lines)
    if not trx:
        return False, "can't find transaction id"

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