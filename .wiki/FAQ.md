# FAQ & Troubleshooting

Common issues and their solutions.

---

## Platform-Specific Issues

### Linux: "adb: command not found"

**Cause:** ADB not installed or not in PATH.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install android-tools-adb

# Fedora
sudo dnf install android-tools

# Arch
sudo pacman -S android-tools
```

### Linux: Dark Mode Not Working

**Cause:** CustomTkinter cannot detect system theme on some Linux distros.

**Solution:**
1. Open the bot GUI
2. In the sidebar, use the **Appearance** dropdown
3. Manually select "Dark" or "Light"

### macOS: "scrcpy: command not found"

**Cause:** scrcpy not installed.

**Solution:**
```bash
brew install scrcpy
```

### macOS: Window Title Bar Not Dark

**Cause:** Tcl/Tk version too old.

**Solution:**
- Use Python installed via Homebrew or Anaconda
- Ensure Tcl/Tk 8.6.9+ is installed

---

## Connection Issues

### "No device found!"

**Cause:** ADB cannot connect to an emulator or device.

**Solutions:**
1. Ensure your emulator is running
2. Enable ADB in emulator settings
3. Check the ADB port (usually 5555, 5557, or 21503)
4. Run `adb devices` to verify connection

```bash
# Windows
.scrcpy\adb connect 127.0.0.1:5555
.scrcpy\adb devices

# Linux/macOS
adb connect 127.0.0.1:5555
adb devices
```

### "adbutils connection failed"

**Cause:** The `adbutils` library cannot connect, falling back to shell commands.

**Solutions:**
1. This is usually a warning, not an error
2. The bot will use system `adb` as fallback
3. Ensure ADB is installed and in PATH

### "scrcpy client failed"

**Cause:** scrcpy touch input is unavailable.

**Solutions:**
1. The bot falls back to `adb shell input tap`
2. Install scrcpy properly if you want low-latency input
3. Check if another scrcpy instance is running

---

## Screenshot Issues

### "Failed to get screen"

**Cause:** Neither adbutils nor shell screencap worked.

**Solutions:**
1. Check ADB connection with `adb devices`
2. Restart the emulator
3. Ensure the game is in foreground
4. Check if `bot_feed_*.png` exists and has non-zero size

### Black/Corrupted Screenshots

**Cause:** Emulator graphics settings or timing issues.

**Solutions:**
1. Use software rendering in emulator
2. Disable GPU acceleration temporarily
3. Increase delays between captures
4. Try a different emulator (LDPlayer, BlueStacks)

---

## Unit Recognition Issues

### "Unit not found under cv-images/all_units/"

**Cause:** Missing template for a deck unit.

**Solutions:**
1. Check spelling matches filename exactly
2. Use `unit_update` mode to capture missing units
3. Ensure `.png` extension is included
4. Check unit exists in appropriate subfolder

### Wrong Unit Detection

**Cause:** Color similarity between units or rank confusion.

**Solutions:**
1. Recapture unit template at current game resolution
2. Check if multiple units have similar color palettes
3. Retrain rank model with more samples
4. Lower `u_prob` threshold in code

### "empty.png" for All Cells

**Cause:** Rank detection returning 0 for all units.

**Solutions:**
1. Verify `rank_model.pkl` exists
2. Retrain model with `python scripts/train_rank_model.py`
3. Check if grid coordinates match your screen resolution

---

## Bot Behavior Issues

### Bot Doesn't Start Battle

**Cause:** UI navigation failing.

**Solutions:**
1. Start on the main menu (home screen)
2. Ensure `battle_icon.png` template is correct
3. Check bot logs for detected icons
4. Manually navigate to battle screen first

### Bot Restarts Constantly

**Cause:** Timeout or state detection failure.

**Solutions:**
1. Check `wait count` in logs
2. Increase timeout threshold (default 40 loops)
3. Verify `fighting.png` template matches current game UI
4. Update game to latest version, then update templates

### Bot Merges Wrong Units

**Cause:** Unit recognition or merge logic error.

**Solutions:**
1. Verify `dps_unit` in config matches template filename
2. Check if unit templates are up-to-date
3. Review merge logic in `bot_core.try_merge()`

---

## Configuration Issues

### "Invalid config format"

**Cause:** Malformed `config.ini`.

**Solutions:**
1. Check for missing `[bot]` section header
2. Verify no trailing commas in lists
3. Use proper boolean values (`True`/`False`)
4. Check encoding is UTF-8

### Units Not Loading

**Cause:** Unit names don't match template files.

**Solutions:**
1. List files in `cv-images/all_units/`
2. Use exact filenames without path
3. Separate units with commas and spaces

```ini
# Correct
units = demon_hunter.png, dryad.png, harlequin.png

# Wrong
units = DemonHunter, Dryad, Harlequin
```

---

## Performance Issues

### High CPU Usage

**Cause:** Continuous screenshot processing.

**Solutions:**
1. Increase `SLEEP_DELAY` in `bot_core.py`
2. Use adbutils (faster than shell commands)
3. Reduce detection frequency
4. Close other applications using ADB

### Slow Screenshot Capture

**Cause:** Using shell fallback instead of adbutils.

**Solutions:**
1. Ensure `adbutils` is installed: `pip install adbutils`
2. Check for connection issues (warning in logs)
3. Use wired connection instead of WiFi ADB

---

## Installation Issues

### "ModuleNotFoundError: No module named 'cv2'"

**Solution:**
```bash
pip install opencv-python
```

### "ModuleNotFoundError: No module named 'adbutils'"

**Solution:**
```bash
pip install adbutils
```

### "ModuleNotFoundError: No module named 'customtkinter'"

**Solution:**
```bash
pip install customtkinter
```

### "No module named 'scrcpy'"

**Note:** scrcpy is optional. The bot works without it.

**If needed:**
```bash
pip install scrcpy-client
```

### rank_model.pkl Compatibility Error

**Error:** `ModuleNotFoundError` or `unsupported pickle protocol` when loading model.

**Cause:** Model was trained with a different Python/scikit-learn version.

**Solution:**
1. Go to GUI → 🧠 Training tab
2. Start the bot to capture some grids
3. Click **🔄 Auto-Label Grid** to generate training data
4. Click **🧠 Train Model** to create a compatible model

### Ruff/Pylance Errors

**Cause:** Development tools not configured.

**Solution:** These are development-only. For running the bot, ignore them.

---

## Logging

### Enable Debug Logging

Edit `Src/bot_logger.py` or set environment:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log File Location

- Console output
- `RR_bot.log` (if file logging enabled)

### Understanding Log Messages

| Pattern | Meaning |
|---------|---------|
| `Connecting to...` | ADB connection attempt |
| `Started scrcpy client` | Touch input ready |
| `fighting, wait count: N` | In battle, N idle frames |
| `home, wait count: N` | On menu, trying to start |
| `RESTARTING due to timeout` | Bot stuck, force restarting |

---

## Getting Help

1. **Check logs** for specific error messages
2. **Verify templates** match current game version
3. **Test ADB connection** manually
4. **Simplify config** to isolate issues
5. **Create issue** with logs and config

### Useful Debug Commands

```bash
# Check ADB connection
.scrcpy\adb devices

# Take manual screenshot
.scrcpy\adb exec-out screencap -p > test.png

# Check game is running
.scrcpy\adb shell dumpsys window | findstr "mCurrentFocus"

# List emulator ports
netstat -an | findstr "555"
```
