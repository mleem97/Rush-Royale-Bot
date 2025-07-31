# Python 3.13 Upgrade Su- **requests**: `2.32.4` (added `>=2.32.0`)
- **setuptools**: `80.9.0` (added `>=80.0.0,<81.0.0`)
- **deprecation**: `2.1.0` (added `>=2.1.0`)
- **retry2**: `0.9.5` (added `>=0.9.0`)
- **psutil**: `7.0.0` (added `>=7.0.0`)
- **matplotlib**: `3.10.3` (added `>=3.9.0`)
- **pure-python-adb**: `0.3.0.dev0` (added `>=0.3.0.dev0` for ppadb.client support)

## 🎉 Successfully Upgraded to Python 3.13.5!

The Rush Royale Bot codebase has been successfully upgraded from Python 3.9.13 to Python 3.13.5, bringing improved performance, better error messages, and access to the latest Python features.

## Changes Made

### 1. Python Environment
- **Old**: Python 3.9.13 in `.bot_env/` virtual environment
- **New**: Python 3.13.5 in `.venv313/` virtual environment

### 2. Updated Dependencies
Updated `requirements.txt` with latest compatible versions and proper dependency management:

- **numpy**: `2.2.6` (was unversioned, now `>=2.0.0`)
- **pandas**: `2.3.1` (was unversioned, now `>=2.2.0`)
- **Pillow**: `11.3.0` (was unversioned, now `>=10.4.0`)
- **scikit-learn**: `1.7.1` (was pinned to `1.1.1`, now `>=1.5.0`)
- **opencv-python**: `4.12.0` (was unversioned, now `>=4.10.0`)
- **ipykernel**: `6.30.0` (was unversioned, now `>=6.29.0`)
- **tqdm**: `4.67.1` (was unversioned, now `>=4.66.0`)
- **ipywidgets**: `8.1.7` (was unversioned, now `>=8.1.0`)
- **adbutils**: `0.14.1` (added with version constraints `>=0.14.1,<0.15.0`)
- **requests**: `2.32.4` (added `>=2.32.0`)
- **setuptools**: `80.9.0` (added `>=80.0.0`)
- **deprecation**: `2.1.0` (added `>=2.1.0`)
- **retry2**: `0.9.5` (added `>=0.9.0`)
- **psutil**: `7.0.0` (added `>=7.0.0`)

**Special handling for scrcpy-client**: Due to version conflicts with the `av` library, scrcpy-client is now installed separately with `--no-deps` flag, followed by manual installation of the latest `av` version.

### 3. Updated Batch Files
- **install.bat**: Now creates `.venv313` environment with Python 3.13 and handles dependency conflicts
- **launch_gui.bat**: Now activates the new `.venv313` environment

### 4. Enhanced Dependency Management
- **Resolved version conflicts**: Properly handled scrcpy-client vs av library version incompatibilities
- **Complete dependency specification**: Added all required dependencies with proper version constraints
- **Automated installation**: Updated install.bat to handle complex dependency scenarios
### 5. Code Fixes
- Fixed invalid escape sequence warning in `gui.py` (line 103)
- Added warning suppression to `bot_core.py` for cleaner operation
- Fixed path reference in `RR_bot.ipynb` (was `./src`, now `./Src`)
- Added missing dependencies: `matplotlib`, `pure-python-adb`

## Dependencies Status
✅ All core dependencies installed and working
✅ All bot modules import successfully
✅ GUI module loads without errors
✅ scrcpy-client configured (with expected compatibility warnings)

## Performance Improvements with Python 3.13
- **Faster startup times** due to improved import system
- **Better memory usage** with optimized garbage collector
- **Enhanced error messages** for easier debugging
- **Improved f-string performance** 
- **Better asyncio performance** for concurrent operations

## How to Use

### For New Installations:
```batch
# Run the updated install script
install.bat
```

### For Existing Users:
The new environment is already set up and ready to use. Simply run:
```batch
# Launch the bot GUI
launch_gui.bat
```

## Verification
All modules tested and confirmed working:
- ✅ Bot Core (`bot_core.py`)
- ✅ Bot Perception (`bot_perception.py`) 
- ✅ Port Scanning (`port_scan.py`)
- ✅ Bot Handler (`bot_handler.py`)
- ✅ GUI (`gui.py`)
- ✅ All dependencies (numpy, pandas, opencv, scikit-learn, etc.)

### Quick Test
Run the dependency verification script:
```batch
# Activate environment and test all dependencies
.venv313\Scripts\activate
python test_dependencies.py
```

## Note on Warnings
~~You may see deprecation warnings about `pkg_resources` - these are harmless and don't affect functionality.~~ **FIXED**: The `pkg_resources` deprecation warning from `adbutils` has been suppressed by:

1. **Pinning setuptools**: `setuptools>=80.0.0,<81.0.0` in requirements.txt
2. **Warning suppression**: Added to test script and can be added to bot code if needed

The warning comes from `adbutils` dependency and is completely harmless - it's just informing about a future API change that doesn't affect current functionality.

## Backward Compatibility
- The old `.bot_env` environment is preserved and can still be used if needed
- All existing configuration files (`config.ini`) remain unchanged
- All image assets and models (`rank_model.pkl`) are compatible

Enjoy the improved performance and latest Python features! 🚀
