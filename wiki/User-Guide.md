# Rush Royale Bot - User Guide

Welcome to the Rush Royale Bot User Guide! This comprehensive guide will help you set up, configure, and use the bot effectively.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Device Setup](#device-setup)
4. [Basic Usage](#basic-usage)
5. [Interface Options](#interface-options)
6. [Configuration](#configuration)
7. [Automation Features](#automation-features)
8. [Troubleshooting](#troubleshooting)
9. [Safety Guidelines](#safety-guidelines)

## Quick Start

### Prerequisites
- Windows, macOS, or Linux system
- Python 3.8 or higher
- Android device with USB debugging enabled
- Rush Royale game installed on your device

### 5-Minute Setup
1. **Install Python** (if not already installed)
2. **Clone or download** the bot files
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Enable USB debugging** on your Android device
5. **Run the bot**: `python -m interface.gui` or `python -m interface.cli`

## Installation

### System Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python Version**: 3.8 or higher
- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: At least 1GB free space
- **USB Port**: For device connection

### Step-by-Step Installation

1. **Install Python**
   ```bash
   # Download from python.org or use package manager
   # Windows: Download from python.org
   # macOS: brew install python
   # Linux: sudo apt install python3 python3-pip
   ```

2. **Download Bot Files**
   ```bash
   git clone https://github.com/your-repo/rush-royale-bot.git
   cd rush-royale-bot
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```bash
   python -m interface.cli diagnostics
   ```

### Optional Dependencies

For enhanced features:
```bash
# For GUI interface
pip install customtkinter pillow

# For advanced debugging
pip install matplotlib seaborn

# For performance monitoring
pip install psutil
```

## Device Setup

### Android Device Configuration

1. **Enable Developer Options**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Developer Options will appear in Settings

2. **Enable USB Debugging**
   - Go to Settings → Developer Options
   - Enable "USB Debugging"
   - Enable "Stay Awake" (recommended)

3. **Connect Device**
   - Connect via USB cable
   - Allow USB debugging when prompted
   - Select "File Transfer" mode

### ADB Setup

The bot includes ADB tools, but you can also install them separately:

```bash
# Windows (using Chocolatey)
choco install adb

# macOS (using Homebrew)
brew install android-platform-tools

# Linux (Ubuntu/Debian)
sudo apt install android-tools-adb
```

### Verify Device Connection

```bash
# Test ADB connection
python -m interface.cli connect

# Or check manually
adb devices
```

## Basic Usage

### Using the Graphical Interface (GUI)

1. **Launch GUI**
   ```bash
   python -m interface.gui
   ```

2. **Connect Device**
   - Click "Connect Device" button
   - Wait for connection confirmation

3. **Configure Settings**
   - Select chapter (1-5)
   - Choose battle type (PvE/PvP)
   - Set maximum battles

4. **Start Bot**
   - Click "Start Bot" for manual control
   - Click "Start Automation" for automatic farming

### Using Command Line Interface (CLI)

1. **Basic Commands**
   ```bash
   # Connect to device
   python -m interface.cli connect
   
   # Run single battle
   python -m interface.cli battle --chapter 3
   
   # Run automation
   python -m interface.cli auto --chapter 2 --count 20
   
   # Show help
   python -m interface.cli help
   ```

2. **Advanced Usage**
   ```bash
   # Debug mode
   python -m interface.cli auto --chapter 3 --debug --verbose
   
   # Specific battle type
   python -m interface.cli battle --type pvp
   
   # System diagnostics
   python -m interface.cli diagnostics
   ```

## Interface Options

### GUI Interface Features

- **Modern Design**: Clean, dark theme interface
- **Real-time Monitoring**: Live battle statistics and progress
- **Screenshot Viewer**: See what the bot sees
- **Performance Metrics**: Detailed automation reports
- **Easy Configuration**: Point-and-click settings

### CLI Interface Features

- **Lightweight**: Minimal resource usage
- **Scriptable**: Easy to automate and integrate
- **Remote Access**: Works over SSH
- **Batch Operations**: Run multiple commands
- **Debug Output**: Detailed logging and error reporting

### Jupyter Notebook Interface

For advanced users and developers:
```bash
jupyter notebook RR_bot.ipynb
```

Features:
- **Interactive Development**: Test and modify bot behavior
- **Data Analysis**: Analyze battle performance
- **Visualization**: Charts and graphs of bot statistics
- **Experimentation**: Try different strategies

## Configuration

### Configuration Files

The bot uses several configuration files:

- `config.ini`: Main bot settings
- `device_config.json`: Device-specific settings
- `automation_config.json`: Automation parameters

### Basic Settings

Edit `config.ini` to customize bot behavior:

```ini
[bot]
default_chapter = 3
battle_timeout = 300
screenshot_delay = 1.0
click_delay = 0.5

[automation]
max_battles_per_session = 50
auto_collect_rewards = true
energy_management = true
retry_failed_battles = true

[recognition]
unit_confidence_threshold = 0.7
template_matching_method = cv2.TM_CCOEFF_NORMED
enable_ml_recognition = true

[debug]
enable_debug_mode = false
save_screenshots = true
log_level = INFO
```

### Advanced Configuration

For power users, additional settings are available:

```ini
[performance]
adaptive_timing = true
performance_monitoring = true
cpu_usage_limit = 80
memory_usage_limit = 1024

[combat]
merge_strategy = aggressive
priority_units = ["shaman", "dryad", "demon_hunter"]
auto_merge_threshold = 0.8
battle_speed = normal

[safety]
max_daily_battles = 200
rest_between_sessions = 1800
random_delays = true
anti_detection_mode = true
```

## Automation Features

### Battle Automation

The bot can automatically:
- **Navigate menus** to start battles
- **Recognize units** on the battlefield
- **Merge units** strategically
- **Collect rewards** after battles
- **Manage energy** and resources
- **Handle errors** and recovery

### Smart Strategies

1. **Merge Optimization**
   - Prioritizes high-value merges
   - Maintains board space efficiently
   - Adapts to different unit types

2. **Energy Management**
   - Monitors energy levels
   - Collects from available sources
   - Optimizes battle timing

3. **Error Recovery**
   - Detects stuck states
   - Automatic navigation recovery
   - Handles game updates gracefully

### Automation Modes

1. **PvE Farming**
   - Continuous dungeon battles
   - Chapter progression
   - Reward collection

2. **Quest Completion**
   - Daily quest automation
   - Achievement hunting
   - Seasonal events

3. **Resource Management**
   - Gold optimization
   - Card collection
   - Upgrade planning

## Troubleshooting

### Common Issues

1. **Device Not Detected**
   ```
   Problem: "No devices found" error
   Solutions:
   - Check USB cable connection
   - Enable USB debugging
   - Install device drivers
   - Try different USB port
   - Restart ADB: adb kill-server && adb start-server
   ```

2. **Battle Not Starting**
   ```
   Problem: Bot can't navigate to battle
   Solutions:
   - Ensure game is open
   - Check screen orientation (portrait mode)
   - Verify game language (English recommended)
   - Update unit templates if needed
   ```

3. **Poor Unit Recognition**
   ```
   Problem: Bot misidentifies units
   Solutions:
   - Check screen resolution compatibility
   - Update unit templates
   - Adjust recognition thresholds
   - Enable debug mode to analyze
   ```

4. **Automation Stops Unexpectedly**
   ```
   Problem: Bot stops working mid-session
   Solutions:
   - Check device battery/power saving
   - Verify stable USB connection
   - Review error logs
   - Increase timeout values
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# CLI debug mode
python -m interface.cli auto --debug --verbose

# Or in config.ini
[debug]
enable_debug_mode = true
log_level = DEBUG
```

Debug mode provides:
- **Screenshot analysis**: See what the bot detects
- **Timing information**: Performance bottlenecks
- **Error details**: Specific failure points
- **Recognition data**: Unit detection confidence

### Log Analysis

Check log files for issues:
- `debug.log`: General bot operations
- `RR_bot.log`: Detailed automation logs
- `debug_output/`: Screenshots and analysis data

### Getting Help

1. **Check Documentation**: Review all wiki pages
2. **Search Issues**: Look for similar problems
3. **Enable Debug Mode**: Gather detailed information
4. **Report Issues**: Provide logs and screenshots

## Safety Guidelines

### Account Safety

1. **Use Responsibly**
   - Don't run 24/7 continuously
   - Take regular breaks between sessions
   - Vary your playing patterns

2. **Detection Avoidance**
   - Enable random delays
   - Use anti-detection features
   - Monitor for game updates

3. **Backup Progress**
   - Link account to Google Play/Game Center
   - Regular manual play sessions
   - Don't rely solely on automation

### System Safety

1. **Resource Monitoring**
   - Monitor CPU and memory usage
   - Ensure adequate cooling
   - Close unnecessary programs

2. **Device Care**
   - Use quality USB cables
   - Avoid overcharging device
   - Monitor device temperature

3. **Data Safety**
   - Regular backups of configurations
   - Keep bot files updated
   - Secure your setup files

### Legal Considerations

- **Terms of Service**: Review game ToS before use
- **Personal Use Only**: Don't distribute or sell accounts
- **Respect Developers**: Support the game through legitimate means
- **Fair Play**: Consider impact on other players

## Best Practices

### Optimal Usage Patterns

1. **Session Management**
   - 30-60 battles per session
   - 2-4 hour breaks between sessions
   - Different times of day

2. **Performance Optimization**
   - Close background applications
   - Use stable power supply
   - Maintain good device connection

3. **Strategy Adaptation**
   - Adjust settings based on results
   - Update templates regularly
   - Monitor success rates

### Maintenance

1. **Regular Updates**
   - Keep bot software updated
   - Update unit templates
   - Review configuration settings

2. **Performance Monitoring**
   - Track success rates
   - Monitor battle times
   - Analyze error patterns

3. **System Health**
   - Clean temporary files
   - Check disk space
   - Monitor system resources

---

## Next Steps

- Review the [Technical Guide](Technical-Guide.md) for advanced configuration
- Check the [API Reference](API-Reference.md) for development
- See [Troubleshooting](Troubleshooting.md) for specific issues

For support and updates, visit our community forums and documentation site.
