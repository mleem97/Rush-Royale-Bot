"""
Lightweight OCR helpers for reading floor numbers from screen captures.
Uses pytesseract (Tesseract OCR engine) with image preprocessing tailored for
high-contrast game UI text.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import cv2
import numpy as np

try:
    import os
    import shutil

    import pytesseract  # type: ignore

    # Try to locate tesseract.exe
    _TESS = True
    _tess_path = os.getenv("TESSERACT_PATH")
    if _tess_path and os.path.exists(_tess_path):
        pytesseract.pytesseract.tesseract_cmd = _tess_path
    else:
        # Common Windows locations
        candidates = [
            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        ]
        found = False
        for c in candidates:
            if os.path.exists(c):
                pytesseract.pytesseract.tesseract_cmd = c
                found = True
                break
        if not found:
            which = shutil.which("tesseract.exe") or shutil.which("tesseract")
            if which:
                pytesseract.pytesseract.tesseract_cmd = which
except Exception:
    _TESS = False


def _prep_digits(img_bgr: np.ndarray) -> np.ndarray:
    """Preprocess ROI to improve OCR on digits: grayscale, CLAHE, blur, threshold, morph."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # Local contrast boost
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    # De-noise but keep edges
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=40)
    # Adaptive threshold
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5)
    # Morph to unify characters
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.dilate(th, kernel, iterations=1)
    # Scale up for better OCR
    h, w = th.shape
    scale = 2 if max(h, w) < 80 else 1
    if scale != 1:
        th = cv2.resize(th, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    return th


def ocr_digits(img_bgr: np.ndarray, psm: int = 7) -> Tuple[Optional[int], float]:
    """Return (number, confidence) if digits are read, else (None, 0).
    psm 7=single line, 6=block; tries strict whitelist for 0-9.
    """
    if not _TESS:
        return None, 0.0
    proc = _prep_digits(img_bgr)
    cfg = f"--psm {psm} -c tessedit_char_whitelist=0123456789"
    try:
        txt = pytesseract.image_to_string(proc, config=cfg).strip()
        # Optional: confidences via image_to_data
        data = pytesseract.image_to_data(proc, config=cfg, output_type=pytesseract.Output.DICT)
        confs = [float(c) for c in data.get("conf", []) if c not in ("-1", None)]
        conf = (sum(confs) / len(confs)) / 100.0 if confs else 0.0
        # Keep only digits
        digits = "".join(ch for ch in txt if ch.isdigit())
        if digits == "":
            return None, conf
        return int(digits), conf
    except Exception:
        return None, 0.0


def read_floor_from_chapter(
    screen_bgr: np.ndarray, chapter_header_xy: Tuple[int, int]
) -> Dict[int, Tuple[Optional[int], float]]:
    """Given the chapter header position (x,y), sample 3 ROIs where floors 1..3 are shown.
    Returns mapping {slot_index: (value, confidence)}. slot_index in {1,2,3} top->bottom.
    """
    x, y = int(chapter_header_xy[0]), int(chapter_header_xy[1])
    h, w, _ = screen_bgr.shape

    # ROIs tuned for 1600x900; adjust with relative offsets around chapter card
    # These offsets might need minor calibration on your device
    rois = {
        1: (x + 10, y - 510, 120, 60),  # top floor label area
        2: (x + 10, y + 470, 120, 60),  # middle floor label area
        3: (x + 10, y + 870, 120, 60),  # bottom floor label area
    }

    results: Dict[int, Tuple[Optional[int], float]] = {}
    for slot, (rx, ry, rw, rh) in rois.items():
        rx0, ry0 = max(0, rx), max(0, ry)
        rx1, ry1 = min(w, rx + rw), min(h, ry + rh)
        if rx1 <= rx0 or ry1 <= ry0:
            results[slot] = (None, 0.0)
            continue
        roi = screen_bgr[ry0:ry1, rx0:rx1]
        # Try psm 7 first, fallback psm 6
        val, conf = ocr_digits(roi, psm=7)
        if val is None or conf < 0.55:
            val2, conf2 = ocr_digits(roi, psm=6)
            if (val2 is not None and conf2 >= conf) or val is None:
                val, conf = val2, conf2
        results[slot] = (val, conf)
    return results


def find_chapter_headers(screen_bgr: np.ndarray) -> Dict[int, Tuple[int, int]]:
    """Locate positions of 'Chapter N' headers on the given screen using OCR.
    Returns mapping {chapter_number: (x, y)} for the top-left of the word 'Chapter'.
    """
    if not _TESS:
        return {}
    try:
        data = pytesseract.image_to_data(screen_bgr, output_type=pytesseract.Output.DICT)
    except Exception as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        return {}
    results: Dict[int, Tuple[int, int]] = {}
    words = [w.strip().lower() for w in data.get("text", [])]
    for i, w in enumerate(words):
        if w == "chapter" and i + 1 < len(words):
            try:
                num = int(words[i + 1])
                x = int(data["left"][i])
                y = int(data["top"][i])
                results[num] = (x, y)
            except (ValueError, TypeError):
                continue
    return results
