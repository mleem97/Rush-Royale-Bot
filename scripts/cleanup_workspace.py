from pathlib import Path
import shutil

import argparse

from __future__ import annotations


def _delete_path(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    if dry_run:
        print(f"DRY-RUN delete: {path}")
        return

    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            return


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Delete generated/local-only artifacts.\n"
            "Safe by default: does not delete venv unless --include-venv is set."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files (default is dry-run).",
    )
    parser.add_argument(
        "--include-venv",
        action="store_true",
        help="Also delete the .bot_env virtual environment.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dry_run = not args.apply

    delete_files = [repo_root / "RR_bot.log"]

    delete_dirs = [
        repo_root / "units",
        repo_root / ".vs",
    ]

    if args.include_venv:
        delete_dirs.append(repo_root / ".bot_env")

    for file_path in delete_files:
        _delete_path(file_path, dry_run=dry_run)

    for path in repo_root.glob("bot_feed_*.png"):
        _delete_path(path, dry_run=dry_run)

    for dir_path in delete_dirs:
        _delete_path(dir_path, dry_run=dry_run)

    # Pattern-based cleanup
    for pattern in [
        "dist/*.zip",
        "**/__pycache__",
        "**/.pytest_cache",
        "**/.ruff_cache",
        "**/.mypy_cache",
        "**/.ipynb_checkpoints",
    ]:
        for path in repo_root.glob(pattern):
            _delete_path(path, dry_run=dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
