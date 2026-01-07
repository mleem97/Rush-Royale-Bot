#!/usr/bin/env bash
# =============================================================================
# Rush Royale Bot - Cross-Platform Installation Script (Linux/macOS)
# =============================================================================
# Usage: ./install.sh [--dev]
#   --dev    Install development dependencies (testing, linting, ML tools)
# =============================================================================
set -e

# Parse arguments
DEV_MODE=false
for arg in "$@"; do
    case $arg in
        --dev)
            DEV_MODE=true
            shift
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "============================================"
echo "   Rush Royale Bot - Installer"
echo "   Linux/macOS Edition"
if [ "$DEV_MODE" = true ]; then
    echo -e "   ${CYAN}[DEVELOPMENT MODE]${BLUE}"
fi
echo "============================================"
echo -e "${NC}"

# 1. Navigate to script directory
cd "$(dirname "$0")"
echo -e "${GREEN}[INFO]${NC} Working directory: $(pwd)"

# 2. Check Python version
echo ""
echo -e "${BLUE}[STEP 1/5]${NC} Checking Python installation..."

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR]${NC} Python not found!"
    echo "Please install Python 3.10 or later:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo -e "${GREEN}[OK]${NC} Found $PYTHON_CMD version $PYTHON_VERSION"

# 3. Check for required system dependencies
echo ""
echo -e "${BLUE}[STEP 2/5]${NC} Checking system dependencies..."

# Check for ADB
if command -v adb &> /dev/null; then
    ADB_VERSION=$(adb --version | head -n1)
    echo -e "${GREEN}[OK]${NC} ADB found: $ADB_VERSION"
else
    echo -e "${YELLOW}[WARN]${NC} ADB not found!"
    echo "The bot requires ADB for Android communication."
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt install android-tools-adb"
    echo "  macOS: brew install android-platform-tools"
    echo ""
fi

# Check for scrcpy
if command -v scrcpy &> /dev/null; then
    SCRCPY_VERSION=$(scrcpy --version 2>&1 | head -n1)
    echo -e "${GREEN}[OK]${NC} scrcpy found: $SCRCPY_VERSION"
else
    echo -e "${YELLOW}[WARN]${NC} scrcpy not found!"
    echo "The bot requires scrcpy for screen mirroring."
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt install scrcpy"
    echo "  macOS: brew install scrcpy"
    echo ""
fi

# 4. Create virtual environment
echo ""
echo -e "${BLUE}[STEP 3/5]${NC} Creating virtual environment..."

VENV_DIR=".bot_env"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[INFO]${NC} Virtual environment already exists. Recreating..."
    rm -rf "$VENV_DIR"
fi

$PYTHON_CMD -m venv "$VENV_DIR"
echo -e "${GREEN}[OK]${NC} Virtual environment created at $VENV_DIR/"

# 5. Activate and install dependencies
echo ""
echo -e "${BLUE}[STEP 4/5]${NC} Installing Python dependencies..."

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip --quiet

# Install requirements based on mode
if [ "$DEV_MODE" = true ]; then
    echo -e "${CYAN}[DEV]${NC} Installing development dependencies..."
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        echo -e "${GREEN}[OK]${NC} All development dependencies installed!"
    else
        echo -e "${RED}[ERROR]${NC} requirements-dev.txt not found!"
        exit 1
    fi
else
    echo -e "${GREEN}[PROD]${NC} Installing production dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo -e "${GREEN}[OK]${NC} All production dependencies installed!"
    else
        echo -e "${RED}[ERROR]${NC} requirements.txt not found!"
        exit 1
    fi
fi

# 6. Verify installation
echo ""
echo -e "${BLUE}[STEP 5/5]${NC} Verifying installation..."

python -c "
import sys
try:
    import customtkinter
    import cv2
    import numpy
    import adbutils
    print('All core packages imported successfully!')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
"

# Done
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
if [ "$DEV_MODE" = true ]; then
    echo -e "${CYAN}   [Development Environment]${NC}"
fi
echo -e "${GREEN}============================================${NC}"
echo ""
echo "To start the bot:"
echo "  ./launch.sh"
echo ""
echo "Or manually:"
echo "  source $VENV_DIR/bin/activate"
echo "  python Src/gui.py"
echo ""
if [ "$DEV_MODE" = false ]; then
    echo "For development setup, run:"
    echo "  ./install.sh --dev"
    echo ""
fi

# Make launch script executable
if [ -f "launch.sh" ]; then
    chmod +x launch.sh
fi
