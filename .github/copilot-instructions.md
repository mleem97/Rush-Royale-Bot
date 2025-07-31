# Rush Royale Bot - AI Assistant Instructions

You are working on a Python 3.13 automation bot for Rush Royale mobile game. This bot runs on Windows with Bluestacks emulator, using computer vision (OpenCV) and machine learning (scikit-learn) for autonomous dungeon farming.

## Key Architecture

**Core Components:**
- `Src/bot_core.py` - Main bot class with ADB/scrcpy communication
- `Src/bot_perception.py` - OpenCV unit recognition (color matching + ORB detection)  
- `Src/gui.py` - Tkinter GUI with real-time combat info
- `Src/bot_handler.py` - Unit management and dependency handling
- `RR_bot.ipynb` - Jupyter notebook for development/manual control

**Device Communication:**
- Uses `scrcpy-client` for screen capture and input injection
- ADB commands via subprocess for device management
- Screen analysis from cached screenshots: `bot_feed_{device_id}.png`
- Target device: `emulator-5554` (Bluestacks default)

**Unit Recognition System:**
- Color-based matching with HSV analysis (`get_color()`, `match_unit()`)
- ML rank detection via `rank_model.pkl` (LogisticRegression)
- Unit images: `all_units/` (source) → `units/` (active deck)
- MSE threshold: 2000 for unit matching confidence

## Development Patterns

**Environment Setup:**
```powershell
python -m venv .venv313
.venv313\Scripts\activate
pip install -r requirements.txt
```

**Running the Bot:**
- Production: `launch_gui.bat`
- Development: `jupyter notebook RR_bot.ipynb`
- Testing: `python test_dependencies.py`

**Device Management Commands:**
```powershell
python tools\fix_multiple_devices.py    # Fix "more than one device" errors
python tools\device_manager.py --list   # List connected devices
python tools\health_check.py            # 7-point system check
```

## Configuration & Conventions

**Bot Configuration (`config.ini`):**
```ini
[bot]
floor = 10              # Dungeon floor target
mana_level = 1,3,5      # Mana upgrade sequence
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter # Primary damage dealer
pve = True              # PvE mode (dungeon farming)
```

**Unit Selection Workflow:**
1. Copy images from `all_units/` to `units/` via `select_units()`
2. Generate color references for active deck
3. Bot uses only units in `units/` folder for recognition

**Critical Patterns:**
- Suppress `pkg_resources` warnings: `warnings.filterwarnings("ignore", message="pkg_resources is deprecated")`
- GUI threading: Bot runs in separate thread to prevent UI blocking
- Screen caching: Reduce ADB calls with `bot_feed_{device_id}.png`
- Performance target: Color analysis optimized for 0.082s execution time

**File Organization:**
- **Production files**: Root directory only
- **Development tools**: `tools/` directory (isolated utilities)
- **Documentation**: `wiki/` directory (technical docs, troubleshooting, changelog)
- **Assets**: `all_units/`, `icons/`, `units/` directories
- **Logs**: `RR_bot.log` in root

**Development vs Production:**
- Development: Use Jupyter notebook for experimentation
- Production: Use GUI or batch files for automated operation
- Tools: Always run from root directory: `python tools\tool_name.py`

## Integration Requirements

**Bluestacks Setup:**
- Resolution: 1600x900 (critical for image recognition)
- ADB enabled on default port (5555)
- Graphics: Compatibility mode for scrcpy stability

**External Dependencies:**
- `scrcpy` binary automatically downloaded if missing
- `rank_model.pkl` for ML-based rank detection
- Batch files handle environment activation automatically

## Testing & Validation

**Dependency Verification:**
```powershell
python test_dependencies.py  # Should show "✅ All 17 modules imported successfully"
```

**Device Health Check:**
```powershell
python tools\health_check.py  # 7-point system check
```

**Documentation & Support:**
- **Troubleshooting**: See `wiki/Troubleshooting.md` for comprehensive issue resolution
- **Technical docs**: See `wiki/Technical-Architecture.md` for system details
- **Tool usage**: See `wiki/Development-Tools.md` for diagnostic utilities

**Common Issues:**
- Multiple devices: Use `fix_multiple_devices.py`
- Missing scrcpy: Auto-downloads in `bot_handler.py`
- Unit recognition fails: Check `units/` folder population and image quality

## Development Guidelines

**Core Requirements:**
- Always use Python 3.13 virtual environment (`.venv313`)
- Follow PEP 8 style guidelines consistently
- Implement comprehensive error handling and logging
- Optimize image processing for 0.082s target performance
- Test on actual Bluestacks device before committing
- Update Gitignore so that only necessary files will be transferred to Github.

**Code Patterns:**
- Use `warnings.filterwarnings()` to suppress known harmless warnings
- Cache screen captures to minimize ADB calls
- Implement graceful fallbacks for device communication failures
- Document complex algorithms with clear docstrings

**Testing Strategy:**
- Run `python test_dependencies.py` before making changes
- Use `python tools\health_check.py` for system validation
- Test unit recognition with actual game screenshots
- Verify GUI responsiveness in separate thread execution
