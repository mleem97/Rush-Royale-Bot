# Installation Guide

## Prerequisites

- **Operating System**: Windows 10/11, Linux, or macOS
- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Android Emulator**: BlueStacks, LDPlayer, MEmu, or similar with ADB enabled

### System Dependencies (Linux/macOS only)

| Dependency | Ubuntu/Debian | macOS (Homebrew) |
|------------|---------------|------------------|
| ADB | `sudo apt install android-tools-adb` | `brew install android-platform-tools` |
| scrcpy | `sudo apt install scrcpy` | `brew install scrcpy` |

> **Note**: On Windows, ADB and scrcpy binaries are bundled in the `.scrcpy/` folder.

## Quick Installation

### Windows

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mleem97/Rush-Royale-Bot.git
   cd Rush-Royale-Bot
   ```

2. **Run the Installer**
   ```batch
   install.bat
   ```
   The installer will:
   - Detect available Python versions
   - Let you choose which Python to use
   - Create a virtual environment (`.bot_env/`)
   - Install all dependencies

3. **Configure Your Units**
   Edit `config.ini` and set your preferred units:
   ```ini
   [bot]
   units = chemist, harlequin, bombardier, dryad, demon_hunter
   ```

4. **Start Your Emulator**
   - Enable ADB in emulator settings
   - Note the ADB port (usually 5555, 5556, etc.)

5. **Launch the Bot**
   ```batch
   launch_gui.bat
   ```

### Linux / macOS

1. **Install System Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3 python3-pip python3-venv android-tools-adb scrcpy

   # macOS
   brew install python3 android-platform-tools scrcpy
   ```

2. **Clone and Install**
   ```bash
   git clone https://github.com/mleem97/Rush-Royale-Bot.git
   cd Rush-Royale-Bot
   chmod +x install.sh launch.sh
   ./install.sh
   ```

3. **Configure Your Units**
   ```bash
   nano config.ini
   # Set: units = chemist, harlequin, bombardier, dryad, demon_hunter
   ```

4. **Launch the Bot**
   ```bash
   ./launch.sh
   ```

## Manual Installation

If the installer fails, you can set up manually:

### Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv .bot_env

# Activate it
.\.bot_env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Linux/macOS (Bash)
```bash
# Create virtual environment
python3 -m venv .bot_env

# Activate it
source .bot_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | ≥1.24.1 | Array operations |
| pandas | ≥2.3.3 | Data analysis |
| opencv-python | ≥4.11.0 | Computer vision |
| scikit-learn | ≥1.7.0 | Machine learning |
| Pillow | ≥10.0 | Image handling |
| adbutils | ≥3.0 | ADB communication |
| av | ≥14.3.0 | Video decoding (scrcpy) |
| tqdm | ≥4.67.1 | Progress bars |
| requests | ≥2.32.3 | HTTP downloads |

## Emulator Setup

### BlueStacks
1. Settings → Advanced → Enable Android Debug Bridge
2. Note the port (default: 5555)

### LDPlayer
1. Settings → Other Settings → Enable ADB
2. Port is shown in settings

### MEmu
1. Settings → Engine → Enable ADB
2. Default port: 21503

## Troubleshooting

### "No device found"
- Verify emulator ADB is enabled
- Check if `adb devices` shows your device
- Try manually connecting: `adb connect 127.0.0.1:5555`

### "adbutils connection failed"
- Ensure only one ADB server is running
- Kill existing servers: `adb kill-server`
- Restart emulator

### Python version issues
- The bot requires Python 3.10+
- Check version: `python --version`
- Install from [python.org](https://python.org)

### Missing rank_model.pkl
- The model file is generated during training
- Run: `python scripts/train_rank_model.py`
- Or use the provided pre-trained model
