from __future__ import annotations

import fnmatch
import os
from pathlib import Path
import time
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

# Keep this explicit and conservative.
EXCLUDE_DIRS = {
    ".git",
    ".vs",
    ".vscode",
    ".bot_env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".ipynb_checkpoints",
    "OCR_inputs",
    "screens",
    "build",
    "dist",
}

EXCLUDE_FILES = {
    ".python_path",
    "RR_bot.log",
    "RB_bot.log",
    "bot_feed.png",
    "bot_feed_emulator-5554.png",
}

EXCLUDE_GLOBS = [
    "*.log",
    "bot_feed_*.png",
    "*.pyc",
]


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)

    # Exclude any path that contains an excluded dir name.
    for part in rel.parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True

    if rel.parts and rel.parts[0] in EXCLUDE_DIRS:
        return True

    if rel.as_posix() in EXCLUDE_FILES or rel.name in EXCLUDE_FILES:
        return True

    for pattern in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(rel.name, pattern):
            return True

    return False


def main() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    zip_path = DIST_DIR / f"Rush-Royale-Bot-{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirnames, filenames in os.walk(REPO_ROOT):
            root_path = Path(root)

            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if not should_exclude(root_path / d)]

            for name in filenames:
                file_path = root_path / name
                if should_exclude(file_path):
                    continue
                rel = file_path.relative_to(REPO_ROOT)
                zf.write(file_path, arcname=rel.as_posix())

    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
