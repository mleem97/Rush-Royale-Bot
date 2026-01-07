# Scripts

Utility scripts in the `scripts/` folder for development and maintenance.

---

## train_rank_model.py

Train the rank recognition ML model.

### Usage

```bash
python scripts/train_rank_model.py [--dataset DIR] [--out FILE]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--dataset` | `machine_learning/inputs` | Directory containing labeled training images |
| `--out` | `rank_model.pkl` | Output path for trained model |

### Dataset Layouts

The script supports two directory structures:

**Layout A (Flat):**
```
machine_learning/inputs/
├── 0_input_1.png
├── 0_input_2.png
├── 1_input_1.png
├── 2_input_1.png
└── ...
```

**Layout B (Nested):**
```
machine_learning/inputs/
├── 0/
│   ├── sample1.png
│   └── sample2.png
├── 1/
│   └── sample1.png
└── ...
```

### Example

```bash
# Train with default settings
python scripts/train_rank_model.py

# Train from custom dataset
python scripts/train_rank_model.py --dataset my_labeled_data/ --out models/rank_v2.pkl
```

### Output

```
Saved: rank_model.pkl
Classes: [0, 1, 2, 3, 4, 5, 6, 7]
```

---

## cleanup_workspace.py

Remove generated files and caches from the workspace.

### Usage

```bash
# Dry run (shows what would be deleted)
python scripts/cleanup_workspace.py

# Actually delete files
python scripts/cleanup_workspace.py --apply

# Also delete virtual environment
python scripts/cleanup_workspace.py --apply --include-venv
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--apply` | Actually delete files (default is dry-run) |
| `--include-venv` | Also delete `.bot_env` virtual environment |

### What Gets Deleted

**Files:**
- `RR_bot.log`
- `bot_feed_*.png` (runtime screenshots)

**Directories:**
- `units/` (legacy folder)
- `.vs/` (Visual Studio cache)
- `.bot_env/` (only with `--include-venv`)

**Pattern-based:**
- `dist/*.zip`
- `**/__pycache__`
- `**/.pytest_cache`
- `**/.ruff_cache`
- `**/.mypy_cache`
- `**/.ipynb_checkpoints`

### Example Output

```
DRY-RUN delete: G:\Programmierung\Rush-Royale-Bot\RR_bot.log
DRY-RUN delete: G:\Programmierung\Rush-Royale-Bot\bot_feed_5555.png
DRY-RUN delete: G:\Programmierung\Rush-Royale-Bot\Src\__pycache__
```

---

## make_release.py

Create a distributable ZIP archive of the project.

### Usage

```bash
python scripts/make_release.py
```

### Output

Creates a timestamped ZIP file in `dist/`:
```
dist/Rush-Royale-Bot-20250101-120000.zip
```

### Exclusions

The script automatically excludes:

**Directories:**
- `.git`, `.vs`, `.vscode`
- `.bot_env` (virtual environment)
- `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`
- `.ipynb_checkpoints`
- `OCR_inputs`, `screens`
- `build`, `dist`

**Files:**
- `.python_path`
- `RR_bot.log`, `RB_bot.log`
- `bot_feed*.png`
- `*.log`, `*.pyc`

### Archive Contents

The resulting ZIP contains everything needed to run the bot:
- Source code (`Src/`)
- CV assets (`cv-images/`)
- Configuration (`config.ini`)
- Dependencies (`requirements.txt`, `pyproject.toml`)
- Documentation (`README.md`, `.wiki/`)
- Launch scripts (`install.bat`, `launch_gui.bat`)

---

## write_tree.ps1

PowerShell script to generate a directory tree listing.

### Usage

```powershell
.\scripts\write_tree.ps1
```

### Output

Writes workspace structure to console or file for documentation purposes.

---

## Adding New Scripts

When creating new utility scripts:

1. Place in `scripts/` folder
2. Add `from __future__ import annotations` for Python 3.13 compatibility
3. Use `Path(__file__).resolve().parents[1]` to get repo root
4. Add `sys.path.insert(0, str(REPO_ROOT / 'Src'))` if importing bot modules
5. Use `argparse` for command-line arguments
6. Return exit codes: `0` for success, non-zero for errors

### Template

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'Src'))


def main() -> int:
    parser = argparse.ArgumentParser(description="Script description")
    # Add arguments...
    args = parser.parse_args()
    
    # Script logic...
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
