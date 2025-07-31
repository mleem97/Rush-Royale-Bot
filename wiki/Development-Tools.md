# Development Tools Guide

## Overview

The `tools/` directory contains all development utilities, diagnostics, and maintenance scripts. These tools are designed to be run from the project root directory.

## Core Development Tools

### Dependency Management

#### `test_dependencies.py`
**Purpose**: Verify all Python dependencies are correctly installed
```powershell
python test_dependencies.py
# Expected output: "✅ All 17 modules imported successfully"
```

**What it checks**:
- Core scientific libraries (NumPy, Pandas, scikit-learn)
- Computer vision (OpenCV, Pillow)
- Android communication (adbutils, pure-python-adb)
- Jupyter support (ipykernel, ipywidgets)
- Utility libraries (tqdm, matplotlib)

### Device Management

#### `device_manager.py`
**Purpose**: Comprehensive ADB device management
```powershell
# List all connected devices
python tools\device_manager.py --list

# Restart ADB server (fixes most connection issues)
python tools\device_manager.py --restart-adb

# Interactive device selection
python tools\device_manager.py --select
```

#### `fix_multiple_devices.py`
**Purpose**: Resolve "more than one device/emulator" errors
```powershell
python tools\fix_multiple_devices.py
```

**What it does**:
1. Lists all connected devices
2. Allows user to select primary device
3. Disconnects other devices automatically
4. Verifies single device connection

#### `fix_devices.bat`
**Purpose**: One-click solution for device conflicts
- Batch wrapper for `fix_multiple_devices.py`
- No command line arguments needed
- Windows-friendly double-click execution

### System Diagnostics

#### `health_check.py`
**Purpose**: Comprehensive 7-point system health check
```powershell
python tools\health_check.py
```

**Checks performed**:
1. Python environment validation
2. Virtual environment status
3. Dependency completeness
4. ADB server status
5. Device connectivity
6. Bluestacks configuration
7. Bot file integrity

#### `advanced_device_diagnostics.py`
**Purpose**: Deep device analysis and troubleshooting
- Detailed device information
- Connection quality assessment
- Performance metrics
- Hardware capability detection

### Version Management

#### `version_info.py`
**Purpose**: Display comprehensive version information
```powershell
python tools\version_info.py
```

**Information shown**:
- Python version and location
- Installed package versions
- System compatibility
- Bot version details

#### `version.py`
**Purpose**: Version string management and utilities
- Centralized version definitions
- Compatibility checking
- Update notifications

## Usage Patterns

### From Project Root
```powershell
# Standard usage pattern
python tools\{tool_name}.py [arguments]

# Examples
python tools\test_dependencies.py
python tools\device_manager.py --list
python tools\health_check.py
```

### Direct Execution
```powershell
# Navigate to tools directory
cd tools

# Run directly
python version_info.py
python health_check.py
```

## Tool Integration

### GUI Integration
- Tools can be called from GUI for diagnostics
- Results displayed in GUI log window
- Background execution supported

### Jupyter Integration
```python
# Import tools in notebook
import sys
sys.path.append('./tools')
import health_check
import device_manager

# Run diagnostics
health_check.run_all_checks()
```

### Batch File Integration
- Automated tool execution in batch files
- Error handling and reporting
- User-friendly prompts and messages

## Development Workflow

### Daily Development
1. **Start session**: `python tools\health_check.py`
2. **Check dependencies**: `python test_dependencies.py`
3. **Verify device**: `python tools\device_manager.py --list`
4. **Begin development**: Launch notebook or GUI

### Troubleshooting Workflow
1. **System check**: `python tools\health_check.py`
2. **Device issues**: `python tools\fix_multiple_devices.py`
3. **Dependency problems**: `python test_dependencies.py`
4. **Advanced diagnostics**: `python tools\advanced_device_diagnostics.py`

### Release Preparation
1. **Version update**: Update `tools\version.py`
2. **Dependency audit**: `python test_dependencies.py`
3. **System compatibility**: `python tools\health_check.py`
4. **Documentation update**: Update tool documentation

## Tool Development Guidelines

### Adding New Tools
1. **Place in tools/ directory**
2. **Follow naming convention**: `snake_case.py`
3. **Include help text**: `--help` argument support
4. **Error handling**: Graceful failure with informative messages
5. **Documentation**: Add to this guide

### Tool Structure Template
```python
#!/usr/bin/env python3
"""
Tool Description: Brief description of tool purpose
Usage: python tools\tool_name.py [arguments]
"""

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Tool description')
    parser.add_argument('--help', action='help')
    args = parser.parse_args()
    
    # Tool logic here
    
if __name__ == '__main__':
    main()
```

### Best Practices
- **Self-contained**: Minimal external dependencies
- **Informative output**: Clear success/failure messages
- **Error codes**: Return appropriate exit codes
- **Logging**: Use consistent logging format
- **Cross-platform**: Consider Windows path conventions

## Maintenance

### Regular Tasks
- Update version information
- Verify tool compatibility with new dependencies
- Test tools with different system configurations
- Update documentation as tools evolve

### Cleanup
- Remove obsolete tools
- Archive old versions
- Maintain consistent coding style
- Update help text and documentation
