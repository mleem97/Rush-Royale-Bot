# 🛠️ Rush Royale Bot - Tools & Utilities

This directory contains development tools, diagnostic utilities, and maintenance scripts for the Rush Royale Bot.

## 📂 Available Tools

### 🔧 System Diagnostics
- **`health_check.py`** - Comprehensive 7-point system health check
  - Python environment validation
  - Virtual environment status  
  - Dependency verification
  - ADB server status
  - Device connectivity
  - Bot file integrity
  - Configuration validation

### 🧪 Development Tools
- **`test_dependencies.py`** - Verify all Python dependencies are correctly installed
  - Tests all 17+ core modules
  - Validates Python 3.13 compatibility
  - Checks scientific libraries (NumPy, OpenCV, scikit-learn)
  - Verifies ADB communication tools
  - Tests Jupyter components

### 🔌 System Utilities
- **`fix_scrcpy_permissions.py`** - Fix scrcpy-related permission issues
  - Resolves ADB permission problems
  - Fixes scrcpy binary access issues
  - Windows-specific permission handling

### 📱 GUI Tools
- **`gui_migration.py`** - GUI migration and compatibility utilities
  - Legacy GUI compatibility support
  - Interface transition helpers
  - Configuration migration tools

## 🚀 Usage

### From Project Root Directory
```batch
# System health check
python tools\health_check.py

# Test all dependencies
python tools\test_dependencies.py

# Fix permission issues
python tools\fix_scrcpy_permissions.py

# GUI migration utilities
python tools\gui_migration.py
```

### Direct Execution
```batch
cd tools
python health_check.py
python test_dependencies.py
```

## 💡 Tips

- **For normal bot usage**: These tools are optional - use `launch_gui.bat` for standard operation
- **For troubleshooting**: Start with `health_check.py` for comprehensive diagnostics
- **For developers**: All tools support `--help` for detailed usage information
- **For automation**: Tools can be integrated into batch scripts and CI/CD pipelines

## 🔄 Tool Integration

### GUI Integration
Tools can be called from the bot GUI for diagnostics and maintenance.

### Batch File Integration
Tools are used by main batch files:
- `health_check.bat` calls `tools\health_check.py`
- `install.bat` uses `tools\test_dependencies.py` for verification

### Development Workflow
1. **Start session**: `python tools\health_check.py`
2. **Verify dependencies**: `python tools\test_dependencies.py`  
3. **Fix issues**: Use appropriate tool based on diagnostics
4. **Begin development**: Launch GUI or notebook

## 📚 Documentation

For detailed technical information, see the main wiki documentation:
- **[Technical Guide](../wiki/Technical-Guide.md)** - Complete technical documentation
- **[User Guide](../wiki/User-Guide.md)** - User-focused documentation
- **[Troubleshooting](../wiki/User-Guide.md#troubleshooting)** - Problem-solving guide

---

*These tools support the Rush Royale Bot v2.1.0+ modular architecture and are not required for normal bot operation.*
