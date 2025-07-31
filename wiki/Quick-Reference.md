# Quick Reference Guide

## 🚀 Standard Usage (Production)

```batch
# 1. Start bot (with automatic health check):
launch_gui.bat

# 2. First-time installation:
install.bat

# 3. Check system health (optional):
health_check.bat

# 4. Use Jupyter Notebook:
# Open RR_bot.ipynb in VS Code or Jupyter
```

## 🛠️ Troubleshooting & Tools

```batch
# Check system status:
python tools\version_info.py

# Test all dependencies:
python tools\test_dependencies.py

# Fix device conflicts ("more than one device" error):
python tools\fix_multiple_devices.py
# or:
tools\fix_devices.bat

# Manage ADB devices:
python tools\device_manager.py --list
python tools\device_manager.py --restart-adb
```

## 📁 File Organization

### 🎮 Production Files (Root Directory):
- `launch_gui.bat` - Start the bot
- `config.ini` - Bot configuration
- `Src/` - Source code
- `RR_bot.ipynb` - Jupyter notebook

### 🛠️ Development Tools (`tools/` folder):
- `test_dependencies.py` - System verification
- `device_manager.py` - Device management
- `fix_multiple_devices.py` - Resolve device conflicts
- `health_check.py` - Comprehensive system check

### 📚 Documentation (`wiki/` folder):
- `Technical-Architecture.md` - System design details
- `Troubleshooting.md` - Comprehensive problem solving
- `Development-Tools.md` - Tool usage guide
- `CHANGELOG.md` - Version history

## ⚡ Common Commands

### Bot Operations
```batch
# Standard startup sequence:
1. launch_gui.bat
2. Configure settings in GUI
3. Click "Start Bot"

# Development mode:
1. Open RR_bot.ipynb
2. Run setup cells
3. Execute bot interactively
```

### Problem Resolution
```batch
# Quick diagnostics:
python tools\health_check.py

# Fix most common issues:
python tools\fix_multiple_devices.py

# Verify installation:
python test_dependencies.py
```

### Configuration
```ini
# Edit config.ini for bot behavior:
[bot]
floor = 10                    # Dungeon floor target
mana_level = 1,3,5           # Mana upgrade sequence
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter      # Primary damage dealer
pve = True                   # PvE mode enabled
```

## 🔧 Unit Management

```python
# Select units for recognition (in Jupyter):
select_units(['chemist', 'harlequin', 'bombardier', 'dryad', 'demon_hunter'])

# Units must exist in all_units/ folder
# Selected units copied to units/ folder for active use
```

## 📊 Performance Tips

- **Resolution**: Ensure Bluestacks is set to 1600x900
- **Graphics**: Use "Compatibility" mode in Bluestacks
- **Resources**: Close unnecessary applications during operation
- **Connection**: Maintain stable internet for ad collection
- **Monitoring**: Check `RR_bot.log` for detailed operation logs

## 🆘 Emergency Commands

```batch
# Bot won't start:
python tools\health_check.py

# Multiple device error:
python tools\fix_multiple_devices.py

# Dependencies missing:
python test_dependencies.py

# Reset environment:
install.bat
```

## 📖 Additional Resources

- **[Troubleshooting Guide](Troubleshooting.md)** - Comprehensive problem solving
- **[Technical Architecture](Technical-Architecture.md)** - System design and internals
- **[Development Tools](Development-Tools.md)** - All tools and utilities
- **[Version History](CHANGELOG.md)** - Complete changelog

---

*For detailed information, see the comprehensive documentation in the wiki folder.*
