# CV Assets

Documentation for the computer vision assets in `cv-images/`.

---

## Directory Structure

```
cv-images/
├── all_units/          # Complete unit template library
│   ├── legendary/      # Legendary unit icons
│   ├── rare/           # Rare unit icons
│   ├── common/         # Common unit icons
│   ├── unit_rank/      # Rank overlay templates (legacy)
│   └── missing_units/  # Captured but unprocessed units
├── icons/              # UI element templates
├── units/              # Active deck templates (runtime)
├── unit_rank/          # Rank detection templates
└── old_icon/           # Deprecated icons (backup)
```

---

## all_units/

Master library containing templates for all recognizable units.

### File Format

- **Format:** PNG
- **Size:** 120×120 pixels (unit icon crop)
- **Naming:** `{unit_name}.png` (lowercase, underscores)

### Example Files

```
all_units/
├── demon_hunter.png
├── dryad.png
├── harlequin.png
├── knight_statue.png
├── shaman.png
├── bombardier.png
└── ...
```

### Adding New Units

1. Use `unit_update` mode in config to capture screenshots
2. Captured images save to `all_units/missing_units/raw_screens/`
3. Crop the unit icon (120×120) from the full screenshot
4. Save as `{unit_name}.png` in appropriate rarity folder

### Subfolders

| Folder | Contents |
|--------|----------|
| `legendary/` | Legendary tier units |
| `rare/` | Rare tier units |
| `common/` | Common tier units |
| `missing_units/` | Raw captures pending processing |

---

## icons/

UI element templates for game state detection.

### Current Icons

| File | Purpose |
|------|---------|
| `battle_icon.png` | Main battle button on home screen |
| `pvp_button.png` | PvP mode selection button |
| `pve_button.png` | PvE/Dungeon mode button |
| `back_button.png` | Navigation back button |
| `cont_button.png` | Continue/confirm button |
| `fighting.png` | In-battle state indicator |
| `dungeon_page.png` | Dungeon selection screen |
| `pve_random.png` | Random co-op button |
| `shaman_opponent.png` | Enemy shaman detection |
| `chapter_*.png` | Dungeon chapter indicators |
| `floor_*.png` | Floor number indicators |

### Template Matching Thresholds

Different icons use different matching thresholds:

| Pattern | Threshold | Reason |
|---------|-----------|--------|
| `chapter_*` | 0.75 (multi-scale) | Variable sizes |
| `dungeon_page` | 0.60 | Low contrast UI |
| `floor_*` | 0.95 | Precise matching |
| `pve_*` | 0.85 | Medium precision |
| Default | 0.80 | Standard matching |

### Adding New Icons

1. Take screenshot when target UI element is visible
2. Crop the element with minimal padding
3. Save as grayscale-friendly PNG
4. Add to `cv-images/icons/` with descriptive name
5. Update threshold in `bot_core.py` if needed

---

## units/

**Runtime-populated folder** containing the active deck templates.

### Purpose

When `bot_handler.select_units()` runs, it copies the player's selected units from `all_units/` to this folder. The perception system then only matches against these 5 units for faster recognition.

### Lifecycle

1. **Empty at startup**
2. **Populated by** `select_units()` based on `config.ini`
3. **Cleared** when deck changes
4. **Read by** `bot_perception.grid_status()`

### Contents During Runtime

```
units/
├── demon_hunter.png
├── dryad.png
├── harlequin.png
├── bombardier.png
└── chemist.png
```

---

## unit_rank/

Templates for rank (star) overlay detection.

### Purpose

Used by the ML model to recognize unit ranks (1-7 stars). Each rank has a distinct visual pattern.

### Training Data Format

For the rank recognition model, images should be:
- **Size:** Same as unit icons (120×120)
- **Content:** Canny edge detection output
- **Naming:** `{rank}_input_{id}.png` or in `{rank}/` subfolders

---

## old_icon/

Deprecated or backup icon templates.

### Purpose

Archive of old icon versions for reference. Not used by the bot at runtime.

---

## Image Preprocessing

### Color Matching (`get_color`)

Unit recognition uses dominant color extraction:

1. Read image as BGR
2. Crop center region (90×90 from offset 15,17)
3. Convert to RGB
4. Quantize colors (÷20 rounding)
5. Return top 5 most common colors

### Edge Detection (`match_rank`)

Rank recognition uses Canny edge detection:

```python
img = cv2.imread(filename, 0)  # Grayscale
edges = cv2.Canny(img, 50, 100)
# Feed to LogisticRegression model
```

---

## Best Practices

### Template Quality

- **Resolution:** Match game resolution (1080p recommended)
- **Cropping:** Consistent positioning across templates
- **Lighting:** Capture during normal gameplay (not transitions)
- **Compression:** Use PNG (lossless) for templates

### File Organization

- Keep templates organized by type/rarity
- Use consistent lowercase naming
- Document any special templates (cursed, buffed states)
- Backup before major changes

### Testing Templates

```python
# Quick test for template detection
import cv2
import numpy as np

template = cv2.imread("cv-images/icons/battle_icon.png", 0)
screen = cv2.imread("bot_feed_5555.png", 0)

result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)

print(f"Best match: {max_val:.2%} at {max_loc}")
```
