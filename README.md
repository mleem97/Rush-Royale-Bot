# Rush-Royale-Bot
🤖 Advanced Python bot for Rush Royale - **Now running on Python 3.13!**

![Python Version](https://img.shields.io/badge/python-3.13.5-blue.svg)
![OpenCV](https://img.shields.io/badge/opencv-4.12.0-green.svg)
![NumPy](https://img.shields.io/badge/numpy-2.2.6-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Optimized for use with Bluestacks on Windows PC

## 📋 Table of Contents
- [✨ Features](#-features)
- [🔧 Latest Updates](#-latest-updates-python-313-upgrade)
- [🚀 Quick Setup Guide](#-quick-setup-guide)
- [⚙️ Configuration](#️-configuration)
- [🛠️ Technical Details](#️-technical-details)
- [🐛 Troubleshooting](#-troubleshooting)
- [📊 Bot Statistics & Monitoring](#-bot-statistics--monitoring)
- [🎯 Supported Game Modes](#-supported-game-modes)

## ✨ Features 
* 🔄 **24/7 Operation** - Farm unlimited gold continuously
* 🏰 **Dungeon Optimized** - Specifically tuned for efficient dungeon farming
* ⚡ **Low Latency** - Direct ADB commands via Scrcpy for instant response
* 🎯 **Smart Detection** - Advanced OpenCV unit recognition with ORB detector
* 🎖️ **Rank Detection** - ML-powered rank identification using scikit-learn
* 🛒 **Auto Management** - Store refresh, ad watching, quest completion, chest collection
* 📊 **Interactive Control** - Jupyter notebook for real-time interaction and unit management
* 🎮 **User-Friendly GUI** - Easy-to-use graphical interface for bot control

## 🔧 Latest Updates (Python 3.13 Upgrade)
* ⚡ **Performance Boost** - Upgraded to Python 3.13.5 for faster execution
* 📦 **Modern Dependencies** - Latest versions of NumPy 2.2, Pandas 2.3, OpenCV 4.12
* 🛡️ **Enhanced Stability** - Updated scikit-learn 1.7 and improved error handling
* 🔧 **Better Compatibility** - Resolved deprecation warnings and syntax issues

![output](https://user-images.githubusercontent.com/71280183/171181226-d680e7ca-729f-4c3d-8fc6-573736371dfb.png)

![new_gui](https://user-images.githubusercontent.com/71280183/183141310-841b100a-2ddb-4f59-a6d9-4c7789ba72db.png)



## 🚀 Quick Setup Guide

### Prerequisites

**Python 3.13** *(Recommended - Latest Version)*

Download and install Python 3.13 from:
- 🔗 [Python 3.13 Official Download](https://www.python.org/downloads/)
- ⚠️ **Important**: Select "Add Python to PATH" during installation
- ✅ Verify installation: Open CMD and run `python --version` (should show Python 3.13.x)

**Bluestacks 5** *(Latest Version)*

Install Bluestacks 5 with these optimal settings:
- 🖥️ **Display Resolution**: 1600 x 900
- 🎮 **Graphics Engine**: Compatibility mode (helps with scrcpy stability)
- 🔧 **Android Debug Bridge**: Enabled (note the port number)

### 📱 Game Setup
1. Set up your Google account in Bluestacks
2. Download and install Rush Royale from Google Play
3. Complete initial game setup

### 🤖 Bot Installation

**Option 1: Automated Setup (Recommended)**
```batch
# Clone or download this repository
# Run the automated installer
install.bat
```

**Option 2: Manual Setup**
```batch
# Create virtual environment with Python 3.13
python -m venv .venv313
.venv313\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 🎮 Running the Bot

**GUI Mode (Recommended)**
```batch
launch_gui.bat
```

**Jupyter Notebook Mode**
```batch
# Activate environment
.venv313\Scripts\activate

# Start Jupyter
jupyter notebook RR_bot.ipynb
```

## ⚙️ Configuration

### Bot Settings (`config.ini`)
```ini
[bot]
floor = 10                    # Dungeon floor to farm
mana_level = 1,3,5           # Mana upgrade levels
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter      # Primary damage dealer
pve = True                   # PvE mode enabled
require_shaman = False       # Shaman requirement
```

### Unit Configuration
- Units can be configured in the GUI or `bot_handler.py`
- Available units are automatically detected from the `all_units/` folder
- Rank detection is handled automatically by the ML model

## 🛠️ Technical Details

### Dependencies (Auto-installed)
- **Python 3.13.5** - Latest Python interpreter
- **NumPy 2.2.6** - Numerical computing
- **Pandas 2.3.1** - Data manipulation
- **OpenCV 4.12.0** - Computer vision
- **scikit-learn 1.7.1** - Machine learning
- **Pillow 11.3.0** - Image processing
- **scrcpy-client 0.4.1** - Android screen control
- **ipywidgets 8.1.7** - Interactive widgets

### System Requirements
- Windows 10/11 (64-bit)
- 4GB+ RAM recommended
- Bluestacks 5 installed and configured
- Stable internet connection for ad watching

## 🐛 Troubleshooting

### Common Issues
- **Python not found**: Ensure Python 3.13 is in your PATH
- **Scrcpy connection failed**: Check Bluestacks ADB settings
- **Unit detection issues**: Verify screen resolution is 1600x900
- **Permission errors**: Run as administrator if needed
- **pkg_resources warning**: Harmless deprecation warning from adbutils - functionality not affected

### Performance Tips
- Close unnecessary applications while running the bot
- Use "Compatibility" graphics mode in Bluestacks
- Ensure stable internet connection for ads
- Monitor system resources during 24/7 operation

## 📊 Bot Statistics & Monitoring

The bot provides real-time monitoring through:
- 📈 **Live combat information** - Unit placement and battle progress
- 🔍 **Unit detection accuracy** - Visual feedback on recognized units
- 📋 **Activity logs** - Detailed logging of all bot actions
- ⏱️ **Performance metrics** - Runtime statistics and efficiency data

## 🎯 Supported Game Modes

- ✅ **PvE Dungeons** - Primary farming mode (floors 1-15)
- ✅ **Quest Completion** - Automatic quest collection
- ✅ **Store Management** - Auto-refresh and purchasing
- ✅ **Ad Collection** - Automated ad chest collection
- ⚠️ **PvP Mode** - Limited support (experimental)

## 🔒 Safety & Fair Play

This bot is designed for:
- ⚡ Efficient farming and progression
- 🎮 Enhancing gameplay experience
- ⏰ Time-saving automation

**Please use responsibly** and in accordance with the game's terms of service.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- 🆕 New unit recognition
- 🎯 Strategy optimization  
- 🐛 Bug fixes and stability
- 📱 Additional game mode support

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Acknowledgments

- Rush Royale game by My.Games
- OpenCV community for computer vision tools
- scrcpy project for Android screen mirroring
- Python community for excellent libraries

---

**Happy Farming! 🎮✨**
