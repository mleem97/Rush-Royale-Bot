#!/usr/bin/env bash
# =============================================================================
# Rush Royale Bot - Launch Script (Linux/macOS)
# =============================================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "============================================"
echo "   Rush Royale Bot"
echo "============================================"
echo -e "${NC}"

# Navigate to script directory
cd "$(dirname "$0")"

# Configuration
VENV_DIR=".bot_env"
MAIN_SCRIPT="Src/gui.py"

# Check virtual environment
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${RED}[ERROR]${NC} Virtual environment not found!"
    echo "Please run './install.sh' first."
    exit 1
fi

# Check main script
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo -e "${RED}[ERROR]${NC} Main script not found: $MAIN_SCRIPT"
    echo "Are you in the correct directory?"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Start the GUI
echo -e "${GREEN}[INFO]${NC} Starting Bot GUI..."
python "$MAIN_SCRIPT"

# Handle exit
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}  BOT TERMINATED WITH ERROR (Code: $EXIT_CODE)${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo "Please check the error messages above."
    read -p "Press Enter to close..."
else
    echo ""
    echo -e "${GREEN}[INFO]${NC} Bot terminated normally."
fi
