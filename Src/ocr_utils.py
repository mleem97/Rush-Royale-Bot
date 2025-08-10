"""
Lightweight OCR helpers for reading floor numbers from screen captures.
Uses pytesseract (Tesseract OCR engine) with image preprocessing tailored for
high-contrast game UI text.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import os
    import shutil

    import pytesseract  # type: ignore

    # Try to locate tesseract.exe
    _TESS = True
    _tess_path = os.getenv("TESSERACT_PATH")
    if _tess_path and os.path.exists(_tess_path):
        pytesseract.pytesseract.tesseract_cmd = _tess_path
        logger.debug("Using tesseract executable at %s", _tess_path)
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
                logger.debug("Found tesseract executable at %s", c)
                found = True
                break
        if not found:
            which = shutil.which("tesseract.exe") or shutil.which("tesseract")
            if which:
                pytesseract.pytesseract.tesseract_cmd = which
                logger.debug("Using tesseract executable from PATH: %s", which)
except Exception:
    _TESS = False
    logger.warning("Tesseract not available, OCR functions will be disabled")


def _prep_digits(img_bgr: np.ndarray) -> np.ndarray:
    """Preprocess ROI to improve OCR on digits: grayscale, CLAHE, blur, threshold, morph."""
    logger.debug("Preprocessing digits ROI with shape %s", img_bgr.shape)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    logger.debug("Converted ROI to grayscale")
    # Local contrast boost
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    logger.debug("Applied CLAHE for local contrast enhancement")
    # De-noise but keep edges
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=40)
    logger.debug("Applied bilateral filter to reduce noise")
    # Adaptive threshold
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5)
    logger.debug("Applied adaptive thresholding")
    # Morph to unify characters
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.dilate(th, kernel, iterations=1)
    logger.debug("Performed morphological operations")
    # Scale up for better OCR
    h, w = th.shape
    scale = 2 if max(h, w) < 80 else 1
    if scale != 1:
        th = cv2.resize(th, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        logger.debug("Resized ROI by factor %s", scale)
    else:
        logger.debug("No resizing applied (scale=1)")
    return th


def ocr_digits(img_bgr: np.ndarray, psm: int = 7) -> Tuple[Optional[int], float]:
    """Return (number, confidence) if digits are read, else (None, 0).
    psm 7=single line, 6=block; tries strict whitelist for 0-9.
    """
    if not _TESS:
        logger.debug("Tesseract not available, skipping OCR")
        return None, 0.0
    logger.debug("Running digit OCR with psm=%s", psm)
    proc = _prep_digits(img_bgr)
    logger.debug("Prepared ROI for OCR with shape %s", proc.shape)
    cfg = f"--psm {psm} -c tessedit_char_whitelist=0123456789"
    try:
        txt = pytesseract.image_to_string(proc, config=cfg).strip()
        logger.debug("Tesseract raw output: '%s'", txt)
        # Optional: confidences via image_to_data
        data = pytesseract.image_to_data(proc, config=cfg, output_type=pytesseract.Output.DICT)
        confs = [float(c) for c in data.get("conf", []) if c not in ("-1", None)]
        conf = (sum(confs) / len(confs)) / 100.0 if confs else 0.0
        digits = "".join(ch for ch in txt if ch.isdigit())
        logger.debug("Filtered digits='%s', confidence=%.2f", digits, conf)
        if digits == "":
            return None, conf
        return int(digits), conf
    except Exception as e:
        logger.debug("pytesseract.image_to_string failed: %s", e)
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
        logger.debug("Slot %s ROI: x=%s y=%s w=%s h=%s", slot, rx, ry, rw, rh)
        if rx1 <= rx0 or ry1 <= ry0:
            logger.debug("Slot %s ROI out of bounds", slot)
            results[slot] = (None, 0.0)
            continue
        roi = screen_bgr[ry0:ry1, rx0:rx1]
        # Try psm 7 first, fallback psm 6
        val, conf = ocr_digits(roi, psm=7)
        logger.debug("Slot %s psm7 result: %s (conf=%.2f)", slot, val, conf)
        if val is None or conf < 0.55:
            logger.debug("Slot %s falling back to psm6", slot)
            val2, conf2 = ocr_digits(roi, psm=6)
            logger.debug("Slot %s psm6 result: %s (conf=%.2f)", slot, val2, conf2)
            if (val2 is not None and conf2 >= conf) or val is None:
                val, conf = val2, conf2
        results[slot] = (val, conf)
        logger.debug("Slot %s final result: %s (conf=%.2f)", slot, val, conf)
    return results


def find_chapter_headers(screen_bgr: np.ndarray) -> Dict[int, Tuple[int, int]]:
    """Locate positions of 'Chapter N' headers on the given screen using OCR.
    Returns mapping {chapter_number: (x, y)} for the top-left of the word 'Chapter'.
    """
    if not _TESS:
        logger.debug("Tesseract not available, cannot find chapter headers")
        return {}
    logger.debug("Running OCR to find chapter headers")
    try:
        data = pytesseract.image_to_data(screen_bgr, output_type=pytesseract.Output.DICT)
    except Exception as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        logger.debug("image_to_data failed: %s", e)
        return {}
    results: Dict[int, Tuple[int, int]] = {}
    words = [w.strip().lower() for w in data.get("text", [])]
    logger.debug("OCR detected %d words", len(words))
    for i, w in enumerate(words):
        if w == "chapter" and i + 1 < len(words):
            try:
                num = int(words[i + 1])
                x = int(data["left"][i])
                y = int(data["top"][i])
                results[num] = (x, y)
                logger.debug("Found chapter %s at (%s, %s)", num, x, y)
            except (ValueError, TypeError):
                logger.debug("Skipping invalid chapter entry at index %s", i)
                continue
    return results
