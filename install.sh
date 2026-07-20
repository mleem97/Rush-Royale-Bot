#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11 or newer." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("RushBot requires Python 3.11 or newer")
print(f"Using Python {sys.version.split()[0]}")
PY

if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter is missing. Install your distribution's Python Tk package:" >&2
  echo "  Debian/Ubuntu: sudo apt install python3-tk" >&2
  echo "  Fedora:        sudo dnf install python3-tkinter" >&2
  echo "  Arch Linux:    sudo pacman -S tk" >&2
  exit 1
fi

if ! command -v adb >/dev/null 2>&1 && [[ ! -x "$ROOT_DIR/.scrcpy/adb" ]]; then
  cat >&2 <<'EOF'
ADB was not found. Install Android SDK Platform Tools, then rerun this script:
  Debian/Ubuntu: sudo apt install adb
  Fedora:        sudo dnf install android-tools
  Arch Linux:    sudo pacman -S android-tools

Alternatively, download Google's current Linux Platform Tools and set ADB_PATH.
EOF
  exit 1
fi

"$PYTHON_BIN" -m venv .bot_env
.bot_env/bin/python -m pip install --upgrade pip setuptools wheel
.bot_env/bin/python -m pip install -r requirements.txt

ADB_PATH_VALUE="$(command -v adb || true)"
if [[ -z "$ADB_PATH_VALUE" && -x "$ROOT_DIR/.scrcpy/adb" ]]; then
  ADB_PATH_VALUE="$ROOT_DIR/.scrcpy/adb"
fi

echo "Installation complete."
echo "ADB: $ADB_PATH_VALUE"
echo "Start with: bash launch_gui.sh"
