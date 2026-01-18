"""
RushBot - Auto-Detect Deck Units
Detects the 5 units in the player's deck from the home screen.
Supports both Template Matching and ML-based recognition.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "unit_classifier.pkl"
LABELS_PATH = PROJECT_ROOT / "models" / "unit_labels.json"


# Deck slot positions on home screen (x, y, width, height)
# The game can run in different orientations/resolutions

# Portrait mode: 1080x1920
DECK_SLOTS_PORTRAIT = [
    (108, 1590, 100, 100),  # Slot 1
    (248, 1590, 100, 100),  # Slot 2
    (388, 1590, 100, 100),  # Slot 3
    (528, 1590, 100, 100),  # Slot 4
    (668, 1590, 100, 100),  # Slot 5
]

# Landscape mode: 1920x1080 (common for emulators)
# Deck is typically on the right side of the screen
DECK_SLOTS_LANDSCAPE = [
    (1520, 580, 80, 80),  # Slot 1
    (1620, 580, 80, 80),  # Slot 2
    (1720, 580, 80, 80),  # Slot 3
    (1820, 580, 80, 80),  # Slot 4
    (1520, 680, 80, 80),  # Slot 5 (might be on second row)
]

# Alternative landscape positions
DECK_SLOTS_LANDSCAPE_ALT = [
    (1480, 550, 90, 90),  # Slot 1
    (1580, 550, 90, 90),  # Slot 2
    (1680, 550, 90, 90),  # Slot 3
    (1780, 550, 90, 90),  # Slot 4
    (1480, 660, 90, 90),  # Slot 5
]


def get_slot_positions(
    screenshot_shape: tuple,
) -> list[list[tuple[int, int, int, int]]]:
    """Get appropriate slot positions based on screenshot orientation.

    Args:
        screenshot_shape: (height, width, channels) of screenshot

    Returns:
        List of slot position sets to try
    """
    height, width = screenshot_shape[:2]

    if width > height:
        # Landscape mode
        return [DECK_SLOTS_LANDSCAPE, DECK_SLOTS_LANDSCAPE_ALT]
    else:
        # Portrait mode
        return [DECK_SLOTS_PORTRAIT]


def load_unit_templates(all_units_dir: Path | str) -> dict[str, np.ndarray]:
    """Load all unit template images.

    Args:
        all_units_dir: Path to directory with unit reference images.

    Returns:
        Dictionary mapping unit names to template images.
    """
    all_units_path = Path(all_units_dir)
    templates = {}

    # Load from main directory first (higher priority)
    for unit_file in all_units_path.glob("*.png"):
        if unit_file.stem not in ("empty", "-"):
            img = cv2.imread(str(unit_file))
            if img is not None:
                templates[unit_file.stem] = img

    # Load from subdirectories (common, rare, legendary)
    for subfolder in ["common", "rare", "legendary"]:
        sub_path = all_units_path / subfolder
        if sub_path.exists():
            for unit_file in sub_path.glob("*.png"):
                if unit_file.stem not in ("empty", "-"):
                    img = cv2.imread(str(unit_file))
                    if img is not None:
                        # Don't overwrite if already exists in main
                        if unit_file.stem not in templates:
                            templates[unit_file.stem] = img

    return templates


def match_template_multi_scale(
    slot_img: np.ndarray,
    template: np.ndarray,
    scales: list[float] | None = None,
) -> float:
    """Match template at multiple scales and return best score.

    Args:
        slot_img: Image of the deck slot.
        template: Unit template image.
        scales: List of scale factors to try.

    Returns:
        Best match score (0-1, higher is better).
    """
    if scales is None:
        scales = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    best_score = 0.0
    slot_h, slot_w = slot_img.shape[:2]

    for scale in scales:
        # Resize template
        new_w = int(template.shape[1] * scale)
        new_h = int(template.shape[0] * scale)

        if new_w <= 0 or new_h <= 0:
            continue
        if new_w > slot_w or new_h > slot_h:
            continue

        resized = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Template matching
        try:
            result = cv2.matchTemplate(slot_img, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
        except cv2.error:
            continue

    return best_score


def detect_deck_from_screenshot(
    screenshot: np.ndarray,
    all_units_dir: Path | str = "cv-images/all_units",
    confidence_threshold: float = 0.4,
) -> list[tuple[str, float]]:
    """Detect all 5 deck units from a home screen screenshot.

    Uses template matching for accurate recognition.
    Each unit can only appear once in a deck (no duplicates).

    Args:
        screenshot: BGR screenshot of the home screen.
        all_units_dir: Path to directory with unit reference images.
        confidence_threshold: Minimum confidence to consider a match.

    Returns:
        List of 5 tuples: [(unit_name, confidence), ...]
    """
    # Load templates
    templates = load_unit_templates(all_units_dir)

    if not templates:
        print("[WARNING] No unit templates found!")
        return [("unknown", 0.0)] * 5

    print(f"[DEBUG] Loaded {len(templates)} unit templates")

    detected: list[tuple[str, float]] = []
    detected_units: set[str] = set()  # Track already detected (no duplicates!)

    # Get slot positions based on orientation
    slots_to_try = get_slot_positions(screenshot.shape)
    print(
        f"[DEBUG] Using {'landscape' if screenshot.shape[1] > screenshot.shape[0] else 'portrait'} mode"
    )

    for slot_idx in range(5):
        best_unit = "unknown"
        best_score = 0.0

        # Try both slot position sets
        for slots in slots_to_try:
            x, y, w, h = slots[slot_idx]

            # Extract slot region (with bounds check)
            if y + h > screenshot.shape[0] or x + w > screenshot.shape[1]:
                continue
            if y < 0 or x < 0:
                continue

            slot_img = screenshot[y : y + h, x : x + w]

            if slot_img.size == 0:
                continue

            # Match against all templates
            for unit_name, template in templates.items():
                # Skip if this unit was already detected (can't have duplicates!)
                if unit_name in detected_units:
                    continue

                score = match_template_multi_scale(slot_img, template)

                if score > best_score and score >= confidence_threshold:
                    best_score = score
                    best_unit = unit_name

        # Add to detected (track to prevent duplicates)
        if best_unit != "unknown":
            detected_units.add(best_unit)

        detected.append((best_unit, best_score))
        print(f"[DEBUG] Slot {slot_idx + 1}: {best_unit} (score: {best_score:.3f})")

    return detected


def detect_deck_from_device(
    bot, save_debug: bool = True, use_ml: bool = True
) -> list[tuple[str, float]]:
    """Detect deck units directly from a connected device.

    Args:
        bot: Bot instance with getScreen() method.
        save_debug: If True, saves the screenshot for debugging.
        use_ml: If True and model exists, use ML-based recognition.

    Returns:
        List of 5 detected units.
    """
    # Take fresh screenshot
    bot.getScreen()

    if bot.screenRGB is None:
        print("[ERROR] Could not get screenshot from device")
        return [("unknown", 0.0)] * 5

    print(f"[DEBUG] Screenshot size: {bot.screenRGB.shape}")

    # Save screenshot for debugging
    if save_debug:
        debug_path = str(PROJECT_ROOT / "debug_homescreen.png")
        cv2.imwrite(debug_path, bot.screenRGB)
        print(f"[DEBUG] Saved screenshot to {debug_path}")

    # Check if ML model exists
    if use_ml and MODEL_PATH.exists() and LABELS_PATH.exists():
        print("[INFO] Using ML-based unit recognition")
        return detect_deck_ml(bot.screenRGB)
    else:
        print("[INFO] Using template matching (no ML model found)")
        return detect_deck_from_screenshot(bot.screenRGB)


# =============================================================================
# ML-based Detection (requires trained model)
# =============================================================================


def extract_features(img: np.ndarray) -> np.ndarray:
    """Extract features from an image for ML classification."""
    # Resize to consistent size
    img = cv2.resize(img, (64, 64))

    # Convert to HSV for color features
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Color histogram
    h_hist = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], None, [8], [0, 256]).flatten()
    v_hist = cv2.calcHist([hsv], [2], None, [8], [0, 256]).flatten()

    # Normalize histograms
    h_hist = h_hist / (h_hist.sum() + 1e-7)
    s_hist = s_hist / (s_hist.sum() + 1e-7)
    v_hist = v_hist / (v_hist.sum() + 1e-7)

    # Edge features using HOG-like descriptor
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Compute gradients
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, angle = cv2.cartToPolar(gx, gy)

    # Quantize angles into bins
    n_bins = 9
    angle_bins = (angle * n_bins / (2 * np.pi)).astype(np.int32) % n_bins

    # HOG for 4x4 cells
    cell_size = 16
    hog_features = []
    for i in range(0, 64, cell_size):
        for j in range(0, 64, cell_size):
            cell_mag = mag[i : i + cell_size, j : j + cell_size]
            cell_ang = angle_bins[i : i + cell_size, j : j + cell_size]
            hist = np.bincount(cell_ang.flatten(), weights=cell_mag.flatten(), minlength=n_bins)
            hog_features.extend(hist / (hist.sum() + 1e-7))

    # Combine all features
    features: np.ndarray = np.concatenate([h_hist, s_hist, v_hist, hog_features])

    return features


def predict_unit_ml(img: np.ndarray) -> tuple[str, float]:
    """Predict unit using ML model.

    Args:
        img: BGR image of a unit slot

    Returns:
        Tuple of (unit_name, confidence)
    """
    try:
        import joblib
    except ImportError:
        return "unknown", 0.0

    if not MODEL_PATH.exists():
        return "unknown", 0.0

    # Load model and labels
    clf = joblib.load(MODEL_PATH)
    with open(LABELS_PATH) as f:
        label_map: dict[int, str] = {int(k): v for k, v in json.load(f).items()}

    # Extract features
    features = extract_features(img).reshape(1, -1)

    # Predict with probability
    proba = clf.predict_proba(features)[0]
    pred_idx = int(np.argmax(proba))
    confidence = proba[pred_idx]

    unit_name = label_map.get(pred_idx, "unknown")

    return unit_name, float(confidence)


def detect_deck_ml(
    screenshot: np.ndarray,
    confidence_threshold: float = 0.5,
) -> list[tuple[str, float]]:
    """Detect deck using ML model.

    Args:
        screenshot: BGR screenshot
        confidence_threshold: Minimum confidence to accept prediction

    Returns:
        List of 5 tuples: [(unit_name, confidence), ...]
    """
    slots_to_try = get_slot_positions(screenshot.shape)

    detected: list[tuple[str, float]] = []
    detected_units: set[str] = set()

    print(
        f"[DEBUG] Using {'landscape' if screenshot.shape[1] > screenshot.shape[0] else 'portrait'} mode (ML)"
    )

    for slot_idx in range(5):
        best_unit = "unknown"
        best_conf = 0.0

        for slots in slots_to_try:
            if slot_idx >= len(slots):
                continue
            x, y, w, h = slots[slot_idx]

            if y + h > screenshot.shape[0] or x + w > screenshot.shape[1]:
                continue
            if y < 0 or x < 0:
                continue

            slot_img = screenshot[y : y + h, x : x + w]
            if slot_img.size == 0:
                continue

            unit, conf = predict_unit_ml(slot_img)

            # Skip duplicates
            if unit in detected_units:
                continue

            if conf > best_conf and conf >= confidence_threshold:
                best_unit = unit
                best_conf = conf

        if best_unit != "unknown":
            detected_units.add(best_unit)

        detected.append((best_unit, best_conf))
        print(f"[DEBUG] Slot {slot_idx + 1}: {best_unit} (confidence: {best_conf:.1%})")

    return detected


def format_unit_name(name: str) -> str:
    """Format unit name for display (snake_case to Title Case)."""
    if name in ("unknown", "-", "empty"):
        return "Unknown"
    return name.replace("_", " ").title()


def unit_name_to_filename(name: str) -> str:
    """Convert unit name to filename format."""
    return name.lower().replace(" ", "_") + ".png"


# Test function
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python detect_deck.py <screenshot.png>")
        print("\nThis will detect the 5 deck units from a home screen screenshot.")
        sys.exit(1)

    screenshot_path = sys.argv[1]
    screenshot = cv2.imread(screenshot_path)

    if screenshot is None:
        print(f"Failed to load: {screenshot_path}")
        sys.exit(1)

    print(f"Screenshot size: {screenshot.shape}")
    print("Detecting deck units...\n")

    detected = detect_deck_from_screenshot(screenshot)

    print("\n" + "=" * 40)
    print("DETECTED DECK:")
    print("=" * 40)
    for i, (unit, conf) in enumerate(detected, 1):
        print(f"  Slot {i}: {format_unit_name(unit):20s} (confidence: {conf:.2%})")
