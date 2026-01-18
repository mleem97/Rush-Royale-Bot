# RushBot 🎮🤖

| ![RushBot Logo](https://github.com/user-attachments/assets/621d866c-864e-42bb-a28a-c8dca66425a0) | RushBot is an advanced Python-based automation bot for Rush Royale that combines computer vision, machine learning, and Android device control. Using OpenCV for real-time game state recognition and scikit-learn for strategic decision-making, the bot can autonomously play Rush Royale on Android devices or emulators. Built with a robust architecture featuring ADB integration for device communication, advanced screenshot processing, and a vendored scrcpy client for efficient screen capture. |
| --- | --- |

## 🔗 Project History & Related Work

This project builds upon the foundation of several Rush Royale bot implementations:

- **Original Project**: [AxelBjork/Rush-Royale-Bot](https://github.com/AxelBjork/Rush-Royale-Bot) - The pioneering work that started it all
- **Fixed Version**: [mleem97/Rush-Royale-Bot](https://github.com/mleem97/Rush-Royale-Bot) - Improved stability and bug fixes
- **AI Redesign**: [Frikadellental/Rush-Royale-AI](https://github.com/Frikadellental/Rush-Royale-AI) - Complete redesign with modern AI approaches

## 🚀 Features

- **Computer Vision Integration**: OpenCV-based image recognition for game state analysis
- **Android Device Control**: Direct communication with Android devices/emulators via ADB
- **Machine Learning**: Scikit-learn powered unit and rank recognition
- **Vendored scrcpy Client**: Built-in Python scrcpy client for fast screen capture
- **GUI Interface**: Modern CustomTkinter-based control panel with real-time logging
- **Cross-Platform**: Runs on Windows, Linux, and macOS
- **Multi-Python Support**: Smart installer detects and lets you choose Python versions (3.10-3.14)
- **PvE/PvP Support**: Configurable game modes with dungeon floor selection

## 🏗️ Project Structure

```text
Rush-Royale-Bot/
├── Src/                      # Main source code
│   ├── gui.py               # Tkinter GUI (RushBot class)
│   ├── bot_core.py          # Core bot logic (Bot class)
│   ├── bot_handler.py       # Bot lifecycle management
│   ├── bot_perception.py    # Computer vision & ML
│   ├── bot_logger.py        # Custom logging with colors
│   ├── port_scan.py         # ADB device detection
│   └── scrcpy_client.py     # Scrcpy wrapper class
├── scrcpy/                   # Vendored scrcpy Python client
│   ├── core.py              # Main Client class
│   ├── control.py           # Touch/key input control
│   └── const.py             # Android keycodes
├── all_units/                # Unit icon templates
├── icons/                    # Screen detection templates
├── install.bat               # Smart Python installer
├── launch_gui.bat            # Start the bot GUI
├── config.ini                # Bot configuration
├── requirements.txt          # Python dependencies
└── RB_bot.ipynb             # Jupyter notebook for testing
```

## 📋 Requirements

- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Android Emulator**: BlueStacks, LDPlayer, MEmu, or similar with ADB enabled
- **Operating System**: Windows, Linux, or macOS

### System Dependencies (Linux/macOS)

| Dependency | Linux (apt) | macOS (brew) |
| --- | --- | --- |
| ADB | `sudo apt install android-tools-adb` | `brew install android-platform-tools` |
| scrcpy | `sudo apt install scrcpy` | `brew install scrcpy` |

> **Note**: On Windows, ADB and scrcpy are bundled in the `.scrcpy/` folder.

### Python Dependencies

| Package | Version | Purpose |
| --- | --- | --- |
| numpy | ≥1.24.1 | Array operations |
| pandas | ≥2.3.3 | Data analysis |
| opencv-python | ≥4.12.0 | Image processing |
| scikit-learn | ≥1.8.0 | ML rank detection |
| adbutils | ≥2.0.0 | ADB communication |
| av | ≥12.0.0 | Video decoding (scrcpy) |
| requests | ≥2.32.0 | HTTP downloads |
| tqdm | ≥4.67.1 | Progress bars |
| Pillow | ≥12.1.0 | Image handling |
| customtkinter | ≥5.2.0 | Modern GUI framework |
| darkdetect | ≥0.8.0 | System theme detection |

## 🛠️ Installation

### Windows (Quick Start)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/mleem97/RushBot.git
   cd RushBot
   ```

2. **Run the installer:**

   ```batch
   install.bat
   ```

   - Automatically detects installed Python versions (WindowsStore, PATH, Scoop, Chocolatey)
   - Lets you choose which Python to use
   - Creates a virtual environment in `.bot_env/`
   - Installs all dependencies

3. **Start the bot:**

   ```batch
   launch_gui.bat
   ```

### Linux / macOS

1. **Install system dependencies:**

   ```bash
   # Ubuntu/Debian
   sudo apt install python3 python3-pip python3-venv android-tools-adb scrcpy

   # macOS
   brew install python3 android-platform-tools scrcpy
   ```

2. **Clone and install:**

   ```bash
   git clone https://github.com/mleem97/RushBot.git
   cd RushBot
   chmod +x install.sh launch.sh
   ./install.sh
   ```

3. **Start the bot:**

   ```bash
   ./launch.sh
   ```

### Development Installation

For development work (includes linting, testing, ML tools):

```bash
# Windows
install.bat --dev

# Linux / macOS
./install.sh --dev

# Or with pip directly
pip install -r requirements-dev.txt
```

**Dev dependencies include:**

| Package | Purpose |
| --- | --- |
| black, ruff, isort | Code formatting & linting |
| pyright, mypy | Type checking |
| pytest, pytest-cov | Testing & coverage |
| ipykernel, notebook | Jupyter support |
| gymnasium, stable-baselines3 | Reinforcement learning |
| mkdocs, mkdocs-material | Documentation |

### Manual Installation

```bash
# Create virtual environment
python -m venv .bot_env
.bot_env\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Or install everything (dev)
pip install -r requirements-dev.txt
```

## 🎯 Usage

### Starting the Bot

1. **Start your Android emulator** with ADB debugging enabled
2. **Launch Rush Royale** on the emulator
3. **Run** `launch_gui.bat`
4. **Click "Start Bot"** in the GUI

### Configuration

Edit `config.ini` to customize:

```ini
[bot]
floor = 10                    # Dungeon floor (PvE)
mana_level = 1,3,5            # Mana upgrade priorities
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter       # Main damage unit
pve = True                    # PvE mode (False = PvP)
require_shaman = False        # Leave if no shaman partner
```

### Emulator Setup

**BlueStacks:**

- Settings → Advanced → Enable Android Debug Bridge (ADB)

**LDPlayer:**

- Settings → Other Settings → Enable ADB debugging

**MEmu:**

- Settings → Engine → Enable ADB

## 📊 How It Works

1. **Device Detection**: `port_scan.py` finds connected ADB devices
2. **Screen Capture**: Vendored scrcpy client captures game frames
3. **Vision Analysis**: `bot_perception.py` uses OpenCV to identify:
   - Current game screen (home, battle, ads, etc.)
   - Unit grid positions and types
   - Unit ranks (using trained ML model)
4. **Decision Making**: `bot_core.py` executes game actions:
   - Summon units
   - Merge matching units
   - Upgrade mana levels
   - Handle ads and popups
5. **GUI Updates**: Real-time display of grid state and logs

## 🔧 Troubleshooting

### "No device found!"

- Ensure emulator is running with ADB enabled
- Check with `adb devices` in terminal
- Restart ADB: `.scrcpy\adb kill-server`

### Bot doesn't recognize units

- Update unit icons in `all_units/` folder
- Ensure game resolution matches expected dimensions

### Python not found

- Install Python 3.10+ from [python.org](https://www.python.org/downloads/)
- Or install via Microsoft Store: `python3.13`

## 🤝 Contributing

Contributions welcome! See our [Wiki](https://rushbot.wiki) for detailed documentation.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is created for educational and research purposes. Use at your own risk. The developers are not responsible for any consequences of using this software.

## ❌ Not Supported Units

The following units are **not fully supported** by the bot and may cause unexpected behavior, as their unique mechanics are not implemented:

- **Twins** - Icons exist (`twins1.png`, `twins2.png`) but special merge logic not implemented
- **Treant** - Unit positioning/merging not handled
- **Mole** - Unit mechanics not compatible with current bot logic

### Unit Support Status

| Rarity | Status |
| -------- | -------- |
| Common | ✅ Full Support |
| Rare | ✅ Full Support |
| Epic | ✅ Full Support |
| Legendary | ⚠️ 31/40 supported - Twins, Treant, Mole + 6 others need implementation (see [Issues](https://github.com/mleem97/RushBot/issues)) |

## 🙏 Acknowledgments

- **AxelBjork** for the original Rush Royale bot implementation
- **leng-yue** for the [py-scrcpy-client](https://github.com/leng-yue/py-scrcpy-client) library
