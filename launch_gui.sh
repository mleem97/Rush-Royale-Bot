#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .bot_env/bin/python ]]; then
  echo "Virtual environment not found. Run: bash install.sh" >&2
  exit 1
fi

exec .bot_env/bin/python Src/gui.py
