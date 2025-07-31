# Rush-Royale-Bot
Python based bot for Rush Royale

![Python Version](https://img.shields.io/badge/python-3.13.5-blue.svg)
![OpenCV](https://img.shields.io/badge/opencv-4.12.0-green.svg)
![NumPy](https://img.shields.io/badge/numpy-2.2.6-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-2.1.0-brightgreen.svg)

## Farm unlimited gold!
* Can run 24/7 and allow you to easily upgrade all available units with gold to spare.
* Optimized to farm dungeon floor 5 

## 📋 Table of Contents
- [✨ Features](#-features)
- [🔧 Latest Updates (v2.1.0)](#-latest-updates-v210)
- [🚀 Quick Setup Guide](#-quick-setup-guide)
- [⚙️ Configuration](#️-configuration)
- [🛠️ Technical Details](#️-technical-details)
- [🐛 Troubleshooting](#-troubleshooting)
- [📊 Bot Statistics & Monitoring](#-bot-statistics--monitoring)
- [🎯 Supported Game Modes](#-supported-game-modes)
- [📝 Changelog](#-changelog)

## ✨ Features 
* 🔄 **24/7 Operation** - Farm unlimited gold continuously
* 🏰 **Dungeon Optimized** - Specifically tuned for efficient dungeon farming
* ⚡ **Low Latency** - Direct ADB commands via Scrcpy for instant response
* 🎯 **Smart Detection** - Advanced OpenCV unit recognition with ML-powered rank detection
* 🎖️ **Rank Detection** - ML-powered rank identification using scikit-learn LogisticRegression
* 🛒 **Auto Management** - Store refresh, ad watching, quest completion, chest collection
* 📊 **Interactive Control** - Jupyter notebook for real-time interaction and unit management
* 🎮 **User-Friendly GUI** - Easy-to-use graphical interface for bot control

## 🔧 Latest Updates (v2.1.0)
### 🏗️ Major Architectural Restructure & Cleanup Release!
* 🗂️ **Modular Architecture** - Complete reorganization into `core/`, `modules/`, `interface/`, `wiki/`
* 🧹 **Aggressive Cleanup** - Removed 50+ redundant files, streamlined to 24 essential components
* 📚 **Enhanced Documentation** - Comprehensive wiki system with technical guides
* 🎯 **Improved Maintainability** - Clear module boundaries and single responsibilities
* 🔧 **Better Organization** - Development tools separated, production files optimized
* ⚡ **Performance Focus** - Cleaner imports and optimized module loading

### 🎉 Previous Major Release (v2.0.0) - Python 3.13 Upgrade
* ⚡ **Performance Boost** - Upgraded to Python 3.13.5 for 15-20% faster execution
* 📦 **Modern Dependencies** - Latest versions of NumPy 2.2, Pandas 2.3, OpenCV 4.12
* 🛡️ **Enhanced Stability** - Updated scikit-learn 1.7 and improved error handling
* 🔧 **Better Compatibility** - Resolved deprecation warnings and syntax issues
* 📊 **Matplotlib Support** - Added plotting capabilities for data visualization
* 🔍 **Enhanced ADB** - Improved Android device communication
* 🧪 **Test Suite** - Comprehensive dependency verification system

> **📋 Full Details**: See [CHANGELOG.md](CHANGELOG.md) for complete release notes

![output](https://user-images.githubusercontent.com/71280183/171181226-d680e7ca-729f-4c3d-8fc6-573736371dfb.png)

![new_gui](https://user-images.githubusercontent.com/71280183/183141310-841b100a-2ddb-4f59-a6d9-4c7789ba72db.png)



## 🚀 Quick Setup Guide

**Prerequisites**
- Windows 10/11
- Python 3.13+ (latest recommended)
- Bluestacks 5 emulator

### 1. Install Python 3.13
Download from [python.org](https://www.python.org/downloads/) (Windows 64-bit installer)
- ✅ Check "Add Python to PATH"
- Verify: `python --version` shows Python 3.13.x

### 2. Install Bluestacks 5
- **Display**: Resolution 1600 x 900
- **Graphics**: Compatibility mode (helps with scrcpy issues)
- **Advanced**: Enable Android Debug Bridge (note the port number)
- Install Rush Royale and set up your account

### 3. Setup Bot
```batch
# Clone/download this repository
# Run the installation script:
install.bat

# Start the bot:
launch_gui.bat
```

### 4. Configuration
- Units and settings are managed through the GUI
- For advanced configuration, edit `config.ini`
- For Jupyter development, use `RR_bot.ipynb`

## 📁 Project Structure (New Modular Architecture)

```
Rush-Royale-Bot/
├── 🏗️ Core Architecture (New Modular Design)
│   ├── core/                   # Essential bot functionality
│   │   ├── bot.py             # Main bot controller
│   │   ├── device.py          # Device communication
│   │   ├── perception.py      # Computer vision
│   │   ├── logger.py          # Logging system
│   │   └── config.py          # Configuration management
│   │
│   ├── modules/               # Specialized components
│   │   ├── combat.py          # Combat strategies
│   │   ├── navigation.py      # Game navigation
│   │   ├── recognition.py     # Advanced unit recognition
│   │   ├── automation.py      # Automation workflows
│   │   └── debug.py           # Debug and monitoring
│   │
│   └── interface/             # User interfaces
│       ├── gui.py             # Modern graphical interface
│       └── cli.py             # Command line interface
│
├── 🎮 Production Files (Root Directory)
│   ├── install.bat            # Setup script
│   ├── launch_gui.bat         # Start the bot
│   ├── health_check.bat       # System diagnostics
│   ├── config.ini             # Bot configuration
│   ├── rank_model.pkl         # ML model for rank detection
│   ├── RR_bot.ipynb          # Jupyter notebook
│   ├── all_units/            # Complete unit image collection
│   ├── units/                # Active unit deck
│   └── icons/                # GUI icons
│
├── 🛠️ Development Tools
│   └── tools/                # All development utilities
│       ├── test_dependencies.py    # System verification
│       ├── device_manager.py       # ADB device management
│       ├── fix_multiple_devices.py # Device conflict resolution
│       ├── health_check.py         # Comprehensive diagnostics
│       ├── version_info.py         # Version information
│       └── README.md               # Tools documentation
│
└── 📚 Documentation
    └── wiki/                  # Complete documentation system
        ├── Technical-Architecture.md  # System design details
        ├── Development-Tools.md       # Tool usage guide
        ├── Troubleshooting.md         # Problem solving
        ├── Quick-Reference.md         # Essential commands
        ├── Python-313-Upgrade.md     # Upgrade documentation
        ├── CHANGELOG.md               # Complete version history
        └── README.md                  # Documentation index
```

**For normal use**: Only interact with files in the root directory  
**For troubleshooting**: Use tools in the `tools/` folder  
**For development**: All utilities and docs are organized separately  
**For technical details**: See comprehensive `wiki/` documentation

## ⚙️ Configuration

### Basic Configuration (GUI)
- Launch the bot with `launch_gui.bat`
- Configure units, strategies, and settings through the interface
- Monitor bot performance and statistics in real-time

### Advanced Configuration (config.ini)
Edit `config.ini` for advanced settings:
```ini
[Bot Settings]
combat_delay = 0.1
recognition_threshold = 2000
auto_refresh_store = true
collect_ads = true

[Debug]
debug_mode = false
save_screenshots = false
```

### Unit Management (Jupyter)
Use `RR_bot.ipynb` for interactive unit management:
```python
# Select units for your deck
select_units(['chemist', 'harlequin', 'bombardier', 'dryad', 'demon_hunter'])
```

## 🛠️ Technical Details

### System Architecture
- **Modular Design**: Clean separation between core, modules, and interface
- **Computer Vision**: OpenCV-based unit recognition with MSE ≤ 2000 threshold
- **Machine Learning**: LogisticRegression for accurate rank detection
- **Device Communication**: Low-latency ADB commands via scrcpy
- **Performance**: Optimized to 0.082s per analysis cycle

### Dependencies
- **Python 3.13.5** - Latest Python for optimal performance
- **NumPy 2.2.6** - Numerical computing
- **OpenCV 4.12.0** - Computer vision
- **Pandas 2.3.0** - Data manipulation
- **scikit-learn 1.7.0** - Machine learning
- **Matplotlib 3.9.0** - Data visualization
- **scrcpy-client** - Screen mirroring and control

## 🐛 Troubleshooting

### Quick Fixes
```batch
# System health check
health_check.bat

# Fix device conflicts
python tools\fix_multiple_devices.py

# Test all dependencies
python tools\test_dependencies.py

# Check version information
python tools\version_info.py
```

### Common Issues
- **"More than one device" error**: Run `python tools\fix_multiple_devices.py`
- **Bot won't start**: Check `health_check.bat` for diagnostics
- **Recognition issues**: Verify Bluestacks resolution is 1600x900
- **Performance problems**: Use Compatibility graphics mode in Bluestacks

### Advanced Troubleshooting
See comprehensive guides in `wiki/`:
- [Troubleshooting.md](wiki/Troubleshooting.md) - Complete problem-solving guide
- [Technical-Architecture.md](wiki/Technical-Architecture.md) - System internals
- [Development-Tools.md](wiki/Development-Tools.md) - Tool usage

## 📊 Bot Statistics & Monitoring

The bot provides comprehensive monitoring:
- **Real-time Performance**: Action timing and success rates
- **Resource Tracking**: Gold farming efficiency
- **Error Recovery**: Automatic issue detection and resolution
- **Debug Mode**: Detailed logging and screenshot capture

## 🎯 Supported Game Modes

- ✅ **Dungeon Farming** (Primary focus - Floor 5 optimized)
- ✅ **Store Management** (Auto refresh, ad watching)
- ✅ **Quest Completion** (Automatic collection)
- ✅ **Ad Chest Collection** (Passive income)
- ⚠️ **PvP Mode** (Basic support - use with caution)

## 📝 Changelog

### Current Version: 2.1.0 (July 31, 2025)
- 🏗️ Complete modular architecture restructure
- 🧹 Aggressive codebase cleanup (50+ files removed)
- 📚 Enhanced documentation system
- 🎯 Improved maintainability and extensibility

### Previous Major Release: 2.0.0
- ⚡ Python 3.13 upgrade for 15-20% performance boost
- 📦 Modern dependency stack
- 🛡️ Enhanced stability and error handling

**Full Details**: [CHANGELOG.md](CHANGELOG.md) | **Technical Docs**: [wiki/](wiki/)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see the development documentation in `wiki/` for guidelines.

## ⚠️ Disclaimer

This bot is for educational purposes. Use responsibly and in accordance with Rush Royale's terms of service.
