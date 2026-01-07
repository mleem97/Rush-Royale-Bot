# Rush Royale Bot Wiki

Welcome to the Rush Royale Bot documentation. This wiki provides comprehensive documentation for all components of the bot.

## Quick Start

1. Run `install.bat` to set up the Python environment
2. Configure units in `config.ini`
3. Start your Android emulator with ADB enabled
4. Run `launch_gui.bat` to start the bot

## Table of Contents

### Getting Started
- [Installation Guide](Installation.md) - Prerequisites and setup instructions
- [Configuration](Configuration.md) - Bot settings and customization
- [FAQ & Troubleshooting](FAQ.md) - Common issues and solutions

### Technical Documentation
- [Architecture Overview](Architecture.md) - System design and data flow
- [Core Modules](Core-Modules.md) - Detailed source code documentation
- [CV Assets](CV-Assets.md) - Computer vision image templates
- [Scripts](Scripts.md) - Utility and maintenance scripts

## Project Structure

```
Rush-Royale-Bot/
├── Src/                      # Main source code
│   ├── bot_core.py          # Bot class, ADB/scrcpy handling
│   ├── bot_handler.py       # Game loop, unit selection
│   ├── bot_perception.py    # CV and ML recognition
│   ├── gui.py               # Tkinter interface
│   └── port_scan.py         # Device discovery
├── scrcpy/                   # Vendored scrcpy Python shim
├── cv-images/                # Computer vision assets
│   ├── all_units/           # Unit icon templates
│   ├── icons/               # UI element templates
│   └── units/               # Active deck (runtime)
├── scripts/                  # Utility scripts
├── .scrcpy/                  # ADB/scrcpy binaries
├── config.ini                # Bot configuration
└── requirements.txt          # Python dependencies
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Device Control | ADB (adbutils) | Android device communication |
| Screen Capture | scrcpy | Fast screen mirroring |
| Computer Vision | OpenCV | Image recognition |
| Machine Learning | scikit-learn | Unit/rank classification |
| GUI | Tkinter | User interface |
| Data Analysis | pandas/numpy | Grid state management |
