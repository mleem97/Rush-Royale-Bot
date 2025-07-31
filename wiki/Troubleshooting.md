# Troubleshooting Guide

## Common Issues & Solutions

### Python Environment Issues

#### Python not found
- **Cause**: Python 3.13 is not in your system PATH
- **Solution**: 
  1. Reinstall Python 3.13 and check "Add Python to PATH"
  2. Or manually add Python to your system PATH
  3. Verify with `python --version`

#### Virtual Environment Issues
- **Cause**: Virtual environment not properly created or activated
- **Solution**:
  ```powershell
  # Recreate environment
  python -m venv .venv313
  .venv313\Scripts\activate
  pip install -r requirements.txt
  ```

### Device Connection Issues

#### Scrcpy connection failed
- **Cause**: Bluestacks ADB settings not properly configured
- **Solution**:
  1. Enable ADB in Bluestacks settings
  2. Note the port number (usually 5555)
  3. Restart Bluestacks if needed
  4. Run device diagnostics: `python tools\device_manager.py --list`

#### "More than one device/emulator" error
- **Cause**: Multiple Android devices/emulators are connected
- **Quick Fix**: `python tools\fix_multiple_devices.py`
- **Manual Fix**: 
  ```powershell
  # List devices
  .scrcpy\adb devices
  # Disconnect extras
  .scrcpy\adb disconnect DEVICE_ID
  ```
- **Prevention**: Only run one Bluestacks instance at a time

### Unit Detection Issues

#### Units not recognized properly
- **Cause**: Screen resolution not set to 1600x900
- **Solution**:
  1. Set Bluestacks display to exactly 1600x900
  2. Use "Compatibility" graphics mode
  3. Check that units folder is populated: `select_units()` in notebook

#### Poor recognition accuracy
- **Cause**: 
  - Wrong graphics settings
  - Outdated unit images
  - Screen scaling issues
- **Solution**:
  1. Verify Bluestacks resolution: 1600x900
  2. Update unit images in `units/` folder
  3. Check MSE threshold (should be ≤ 2000)

### Performance Issues

#### Bot running slowly
- **Solutions**:
  - Close unnecessary applications
  - Use "Compatibility" graphics mode in Bluestacks
  - Ensure stable internet connection
  - Monitor system resources during operation

#### High CPU/memory usage
- **Solutions**:
  - Limit concurrent processes
  - Use GUI mode instead of notebook for production
  - Check for memory leaks in long-running sessions

### Permission & Access Issues

#### Permission errors
- **Solution**: Run as administrator if needed
- **Alternative**: Check file permissions in bot directory

#### File access errors
- **Cause**: Antivirus or file locks
- **Solution**:
  1. Add bot directory to antivirus exceptions
  2. Close other applications accessing bot files
  3. Restart if files are locked

### Warning Messages

#### pkg_resources deprecation warning
- **Message**: "pkg_resources is deprecated"
- **Status**: Harmless - functionality not affected
- **Cause**: Legacy dependency from adbutils
- **Note**: Already suppressed in bot code

## Device Management Tools

### Available Commands
```powershell
# List all connected devices
python tools\device_manager.py --list

# Restart ADB server
python tools\device_manager.py --restart-adb

# Interactive device selection
python tools\device_manager.py --select

# Fix multiple device conflicts
python tools\fix_multiple_devices.py

# Comprehensive health check
python tools\health_check.py
```

### Diagnostic Steps
1. **Check Python environment**: `python --version`
2. **Verify dependencies**: `python test_dependencies.py`
3. **Test device connection**: `python tools\device_manager.py --list`
4. **Check Bluestacks settings**: Resolution 1600x900, ADB enabled
5. **Validate unit images**: Ensure `units/` folder is populated
6. **Test bot initialization**: Start with GUI mode first

## Version Migration

### From v1.x to v2.0
- Install Python 3.13
- Run `install.bat` 
- Existing configs preserved ✅
- No manual configuration needed

### First-time Installation
- Follow Quick Setup Guide in main README
- Use automated installer: `install.bat`
- Verify with dependency check

### Rollback Strategy
- Keep old `.bot_env` folder as backup
- Maintain separate Python 3.9 environment if needed
- Document any custom configurations before upgrade

## Getting Help

1. **Check this troubleshooting guide first**
2. **Run diagnostic tools**: `python tools\health_check.py`
3. **Check logs**: Review `RR_bot.log` for error details
4. **Test in isolation**: Use individual tools to identify issues
5. **Report bugs**: Include log files and system information
