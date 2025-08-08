# Rush Royale Bot - AI Coding Assistant Instructions

## Project Overview

This is a Python 3.13-compatible game automation bot for "Rush Royale" with hybrid RL (Reinforcement Learning) capabilities. The project combines traditional computer vision-based automation with emerging ML/RL features. Originally based on AxelBjork's work, this version adds modern Python 3.13 support, enhanced error handling, and planned RL integration.
NEVER USE MOCK DATA! NEVER USE EMOJIS! ONLY PYTHON 3.13-3.15! NEVER ADD ANY FILES. ONLY USE #CODEBASE and .bot_env!
**Target Environment**: BlueStacks Android emulator on Windows with ADB connectivity on port 5555.
**Dev Environment**: Python 3.13-3.15, Windows 10/11, ADB installed and accessible, powershell.

## Architecture & Core Components

### Primary Entry Points
- **GUI Mode**: `Src/gui.py` - Legacy Tkinter interface for interactive control with real-time combat display
- **Notebook Mode**: `RR_bot.ipynb` - Development/experimentation environment for RL research
- **Batch Scripts**: `launch_gui.bat`, `install.bat` - Windows convenience launchers with virtual environment activation

### Detailed System Architecture
```
Bot Core (bot_core.py)
├── ADB Client Management (pure-python-adb primary, shell fallback)
├── Screenshot System (scrcpy → ppadb → shell screencap)
├── Touch/Swipe Commands (with human-like timing delays)
└── Game State Navigation (force restart, menu detection)
    ↓
Bot Handler (bot_handler.py)
├── Main Game Loop (combat detection, ad watching, state transitions)
├── Combat Strategy (mana management, unit merging, grid analysis)
├── Unit Selection System (dynamic unit copying from all_units/ to units/)
└── Configuration Management (config.ini live updates)
    ↓
Bot Perception (bot_perception.py)
├── Computer Vision Pipeline (template matching + color analysis)
├── ML Unit Classification (sklearn LogisticRegression for ranks)
├── Grid State Analysis (3x5 combat grid with age tracking)
└── Unit Recognition (color-based matching with MSE < 2000 threshold)
    ↓
GUI (gui.py)
├── Threading Coordination (main GUI + bot execution threads)
├── Real-time Display (combat grid, unit stats, merge analysis)
├── Configuration Interface (mana targets, floor selection, unit choices)
└── Log Feed Integration (live bot status and debug information)
```

### Critical Data Flow & State Machine
1. **Screenshot Capture Pipeline**:
   ```python
   # Priority order with fallbacks
   _try_scrcpy_screenshot() → _try_adb_screenshot() → _try_shell_screenshot()
   # Validation: file size > 1000 bytes, valid CV2 image loading
   ```

2. **Image Recognition Cascade**:
   ```python
   # Template matching for UI elements (threshold=0.8)
   icons_df = get_current_icons() → pandas DataFrame with [icon, available, pos]
   # Color-based unit matching (MSE distance)
   unit_colors = get_color(filename, crop=True) → 5 most common RGB values
   # ML rank classification
   rank, probability = match_rank(filename) → sklearn LogisticRegression prediction
   ```

3. **Game State Detection**:
   ```python
   # Icon-based state machine transitions
   'fighting' → combat_loop() → mana_level() + merge_unit()
   'home' → watch_ads() → refresh_shop() → battle_screen()
   'menu' → click_button() → navigate to target state
   'lost' → key_input(KEYCODE_BACK) → force navigation
   ```

4. **Action Execution with Timing**:
   ```python
   # Human-like interaction patterns
   click(x, y, delay_mult=1) → time.sleep(SLEEP_DELAY * delay_mult)
   click_button(pos) → coords + 10px offset + 10x delay multiplier
   swipe(start, end) → 300ms duration with grid coordinate mapping
   ```

## Key Development Patterns & Implementation Details

### Configuration System Architecture
- **Central Config**: `config.ini` with INI format sections [bot], [rl_system], [dqn_config], [ppo_config]
- **Live GUI Updates**: Tkinter variables sync with config file writes via `update_config()`
- **Unit Selection Mechanism**: File copying from `all_units/` to `units/` directory for active deck
- **Dynamic Config Loading**: `configparser.ConfigParser()` with real-time validation

```python
# Config update pattern used throughout
self.config.read('config.ini')
self.config['bot']['floor'] = str(floor_var)
self.config['bot']['mana_level'] = np.array2string(card_level, separator=',')[1:-1]
with open('config.ini', 'w') as configfile:
    self.config.write(configfile)
```

### Computer Vision Pipeline Details
```python
# Standard icon detection pattern (used 20+ times)
icons_df = bot.get_current_icons(available=True)
if (icons_df == 'target_icon.png').any(axis=None):
    pos = get_button_pos(icons_df, 'target_icon.png')
    bot.click_button(pos)

# Unit color analysis for recognition
def get_color(filename, crop=False):
    unit_img = cv2.imread(filename)
    if crop:
        unit_img = unit_img[15:15 + 90, 17:17 + 90]  # Specific crop coordinates
    flat_img_round = flat_img // 20 * 20  # Round to nearest 20 for color grouping
    unique, counts = np.unique(flat_img_round, axis=0, return_counts=True)
    # Return 5 most common colors for matching

# Grid coordinate system (critical for unit placement)
def get_grid():
    top_box = (153, 945)  # Fixed pixel coordinates for grid start
    box_size = (120, 120)  # Each grid cell dimensions
    gap = 0  # No gap between cells
    height, width = 3, 5  # 3x5 combat grid
    # Generate numpy array of (x,y) coordinates for each grid position
```

### Grid-based Game State Management
- **3x5 Combat Grid**: Fixed pixel mapping at coordinates (153, 945) with 120x120 cells
- **Unit Recognition**: Color matching with MSE < 2000 threshold + ML rank classification  
- **Age Tracking**: Pandas DataFrames track unit consistency across game frames
- **Merge Logic**: Complex algorithms for unit combination strategies

```python
# Grid analysis pattern used in combat_loop
grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)

# Advanced filtering for merge decisions
merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)  # Remove max ranks
merge_prio = adv_filter_keys(merge_series, 
                           units=['chemist.png', 'bombardier.png', 'summoner.png'])
```

### Threading & Synchronization Patterns
- **Main Thread**: Tkinter GUI event loop with `root.mainloop()`
- **Bot Thread**: Game automation logic in `threading.Thread(target=bot_loop)`
- **Info Thread**: Real-time data sharing via `threading.Event()` coordination
- **Thread Safety**: GUI updates through `root.update_idletasks()` only

```python
# Critical threading pattern for GUI updates
def start_bot(self):
    infos_ready = threading.Event()
    thread_bot = threading.Thread(target=bot_handler.bot_loop, args=([bot, infos_ready]))
    thread_bot.start()
    while(1):
        infos_ready.wait(timeout=5)  # Block until bot has new data
        self.update_text(bot.combat_step, bot.combat, bot.output, ...)
        infos_ready.clear()
        if self.stop_flag:
            bot.bot_stop = True
            thread_bot.join()  # Clean thread termination
```

### Error Handling & Resilience Strategies
- **Multi-method Screenshots**: 3-tier fallback system with different ADB approaches
- **ADB Connection Recovery**: Automatic device re-enumeration and reconnection
- **Game State Recovery**: Force restart mechanisms for stuck states
- **Computer Vision Validation**: File size checks, image loading verification

```python
# Screenshot fallback pattern (critical for reliability)
def getScreen(self):
    if self._try_scrcpy_screenshot(screenshot_path):
        self.logger.debug('Screenshot via scrcpy')
    elif self._try_adb_screenshot(screenshot_path):
        self.logger.debug('Screenshot via pure-python-adb')
    elif self._try_shell_screenshot(screenshot_path):
        self.logger.debug('Screenshot via ADB shell')
    else:
        self.logger.error('All screenshot methods failed!')
        return
```

## Development Workflows & Detailed Setup

### Environment Setup & Dependencies
```bash
# Python 3.13 virtual environment required
python -m venv .bot_env
.bot_env\Scripts\activate
pip install -r requirements.txt

# Key dependencies with version constraints:
# pure-python-adb>=0.3.0 (primary Android control)
# opencv-python>=4.10.0 (computer vision)
# scikit-learn>=1.5.0 (ML rank classification)
# numpy>=1.24.0,pandas>=2.0.0 (data processing)
```

### Enhanced Installation Process
1. **Automated Installation**: `install.bat` with comprehensive Python version checking
2. **System Validation**: `debug_start.bat` runs full system check before launch
3. **Error Recovery**: Improved fallback mechanisms and dependency validation

### Installation Scripts Features
- **Python Version Validation**: Requires Python 3.11+ with clear error messages
- **Dependency Installation**: Individual package installation with error handling
- **Environment Validation**: Checks all critical components before bot start
- **Auto-Config Creation**: Generates default config.ini if missing

### Debugging Workflow
```batch
# Enhanced installation with validation
install.bat

# System diagnostic before running
debug_start.bat  # Runs system_check.py + launches GUI

# Standard launch (with built-in validation)
launch_gui.bat
```

### Android Device Setup (Critical Steps)
1. **BlueStacks Configuration**:
   ```
   Settings → Advanced → Android Debug Bridge: Enabled
   Port: 5555 (hardcoded in bot_core.py)
   Performance → CPU: 4+ cores, RAM: 8GB+ recommended
   Display → Resolution: Must match screenshot coordinates (1600x900 optimal)
   ```

2. **ADB Connection Verification**:
   ```python
   # Test ADB connectivity before running bot
   from ppadb.client import Client as AdbClient
   client = AdbClient()
   devices = client.devices()  # Should show emulator-5554 or similar
   ```

### Testing & Debugging Workflows
- **Enhanced Installation**: `install.bat` with Python version validation and dependency checking
- **System Diagnostics**: `Src/system_check.py` validates environment, dependencies, and ADB connection
- **Debug Launch**: `debug_start.bat` runs full system check before GUI launch
- **Screenshot Inspection**: Check `bot_feed_emulator-5554.png` for vision issues
- **Icon Detection Debug**: Use `get_current_icons()` with `available=False` to see all matches
- **Grid Analysis**: Inspect `OCR_inputs/` directory for unit recognition problems
- **State Machine Debug**: Log output shows current state transitions
- **Threading Issues**: Check for `threading.Event` deadlocks in GUI updates

```python
# Debug icon detection (use in console)
bot = bot_core.Bot()
icons_df = bot.get_current_icons(available=False)
print(icons_df[icons_df['available'] == True])  # See what's detected

# Debug grid recognition
names = bot.scan_grid(new=True)
grid_df = bot_perception.grid_status(names)
print(grid_df[['unit', 'rank', 'u_prob', 'r_prob']])  # Check recognition accuracy

# Run comprehensive system check
python Src/system_check.py
```

### Adding New Features (Step-by-Step)

#### 1. New Game Actions (Extend bot_core.py)
```python
# Pattern for new ADB commands
def new_action(self, x, y, action_type='tap'):
    if self.adb_device:
        if action_type == 'tap':
            self.adb_device.input_tap(x, y)
        elif action_type == 'swipe':
            self.adb_device.input_swipe(x, y, x2, y2, duration)
    else:
        # Always provide shell fallback
        self.shell(f'input {action_type} {x} {y}')
    time.sleep(SLEEP_DELAY)  # Critical for timing
```

#### 2. UI Elements (Add to icons/ directory)
- Add `.png` files to `icons/` directory
- Use template matching threshold of 0.8 in `get_current_icons()`
- Test with `cv2.matchTemplate()` to verify recognition
- Update `valid_targets` list in `getXYByImage()` if needed

#### 3. Unit Types (Add to all_units/ directory)
```python
# Unit addition workflow
# 1. Add unit image to all_units/
# 2. Run color analysis to verify matching
unit_colors = bot_perception.get_color('all_units/new_unit.png', crop=True)
# 3. Test MSE distance with existing units
# 4. Add to config.ini units list for selection
```

#### 4. Config Options (Update config.ini structure)
```ini
# Add new sections following existing pattern
[new_feature]
enabled = True
parameter = value

# Update GUI in create_options() function
new_var = IntVar(value=config.getint('new_feature', 'parameter'))
new_widget = Checkbutton(frame, text='New Feature', variable=new_var)
```

## Critical Integration Points & Technical Deep-Dive

### Android Device Communication Layer
- **Primary Method**: `pure-python-adb` for reliable cross-platform device control
- **Screenshot Priority**: scrcpy executable → ppadb.screencap() → shell ADB screencap
- **Connection Management**: Automatic device enumeration with reconnection logic
- **Fallback Strategy**: Shell ADB commands if Python ADB client fails

```python
# ADB connection initialization pattern
self.adb_client = AdbClient()
devices = self.adb_client.devices()
for dev in devices:
    if dev.serial == self.device:
        self.adb_device = dev
        break
# Always test connection before actions
if not self.adb_device:
    self.shell(f'adb connect {self.device}')
```

### Machine Learning & Computer Vision Components
- **Unit Recognition**: Two-stage process (color matching + rank classification)
- **Color Analysis**: 5 most common RGB values rounded to nearest 20 for noise reduction
- **ML Model**: sklearn LogisticRegression trained on Canny edge detection features
- **Model Persistence**: `rank_model.pkl` stores trained classifier
- **Training Pipeline**: `bot_perception.add_grid_to_dataset()` → `quick_train_model()`

```python
# Unit recognition workflow
def match_unit(filename, ref_colors, ref_units):
    unit_colors = get_color(filename, crop=True)  # Crop to 90x90 center
    for color in unit_colors:
        mse = np.sum((ref_colors - color)**2, axis=1)
        if mse[mse.argmin()] <= 2000:  # MSE threshold
            return ref_units[mse.argmin()], round(mse[mse.argmin()])
    return ['empty.png', 2001]  # Default to empty if no match

# Rank classification
def match_rank(filename):
    img = cv2.imread(filename, 0)
    edges = cv2.Canny(img, 50, 100)  # Edge detection
    with open('rank_model.pkl', 'rb') as f:
        logreg = pickle.load(f)
    prob = logreg.predict_proba(edges.reshape(1, -1))
    return prob.argmax(), round(prob.max(), 3)
```

### State Management & Threading Architecture
- **Main Thread**: Tkinter GUI event loop (`root.mainloop()`)
- **Bot Thread**: Game automation execution (`threading.Thread(target=bot_loop)`)
- **Data Sharing**: `threading.Event()` for synchronized information updates
- **Thread Safety**: All GUI updates must use `root.update_idletasks()`

```python
# Threading coordination pattern (critical for stability)
def start_bot(self):
    infos_ready = threading.Event()
    thread_bot = threading.Thread(target=bot_handler.bot_loop, args=([bot, infos_ready]))
    thread_bot.start()
    
    while True:
        infos_ready.wait(timeout=5)  # Block until bot thread signals
        # Update GUI with thread-safe methods only
        self.update_text(bot.combat_step, bot.combat, bot.output, ...)
        infos_ready.clear()  # Reset event for next iteration
        
        if self.stop_flag:
            bot.bot_stop = True  # Signal bot thread to stop
            thread_bot.join()    # Wait for clean thread termination
            break
```

### Game State Detection & Navigation Logic
- **State Machine**: Icon-based detection with pandas DataFrame analysis
- **Combat Detection**: `fighting.png` template matching
- **Navigation**: Back button detection and forced navigation via KEYCODE_BACK
- **Ad Watching**: Automated sequence for resource collection
- **Error Recovery**: Multi-level restart mechanisms

```python
# State detection pattern used throughout bot_handler.py
def battle_screen(self, start=False, pve=True, floor=5):
    df = self.get_current_icons(available=True)
    if not df.empty:
        if (df == 'fighting.png').any(axis=None):
            return df, 'fighting'  # In combat
        if (df == 'home_screen.png').any(axis=None):
            if start:
                # PvE vs PvP button selection
                button_pos = [640, 1259] if pve else [140, 1259]
                self.click_button(np.array(button_pos))
            return df, 'home'
        # Handle other UI states...
    self.key_input(const.KEYCODE_BACK)  # Force navigation
    return df, 'lost'
```

### Combat Strategy & Unit Management
- **Merge Priority System**: High-value units (chemist, bombardier) merged first
- **Special Unit Handling**: Harlequin copying, Dryad synergies, preserve logic
- **Board Analysis**: Grid fullness detection, age tracking, rank optimization
- **Mana Management**: Card upgrade sequences based on user configuration

```python
# Complex merge decision algorithm
def try_merge(self, rank=1, prev_grid=None, merge_target='zealot.png'):
    grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
    df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
    
    merge_series = unit_series.copy()
    merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
    
    # Priority merge system
    merge_prio = adv_filter_keys(merge_series,
                               units=['chemist.png', 'bombardier.png', 'summoner.png'])
    if not merge_prio.empty:
        merge_df = self.merge_unit(df_split, merge_prio)
    
    # Board management logic
    if df_groups['empty.png'] <= 2:  # Board getting full
        low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
        if not low_series.empty:
            merge_df = self.merge_unit(df_split, low_series)
```

## Common Pitfalls & Detailed Solutions

### Android Connection Issues
**Problem**: ADB device not found or connection drops
```python
# Diagnostic steps
from ppadb.client import Client as AdbClient
client = AdbClient()
devices = client.devices()
if not devices:
    # Check BlueStacks ADB settings
    # Ensure port 5555 is enabled
    # Try manual connection
    subprocess.run(['adb', 'connect', '127.0.0.1:5555'])
```

**Solutions**:
- Ensure BlueStacks ADB enabled on port 5555 (hardcoded in bot_core.py)
- Check Windows firewall isn't blocking ADB connections
- Restart BlueStacks if device enumeration fails
- Use `port_scan.py` to verify device availability

### Computer Vision Problems
**Problem**: Icon detection fails or unit recognition inaccurate
```python
# Debug screenshot quality
screenshot_path = f'bot_feed_{self.bot_id}.png'
if os.path.exists(screenshot_path):
    file_size = os.path.getsize(screenshot_path)
    if file_size < 1000:  # File too small
        self.logger.warning(f'Screenshot file corrupted: {file_size} bytes')
        
# Test template matching manually
import cv2
img_gray = cv2.cvtColor(self.screenRGB, cv2.COLOR_BGR2GRAY)
template = cv2.imread('icons/home_screen.png', 0)
res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
max_val = res.max()  # Should be > 0.8 for detection
```

**Solutions**:
- Validate screenshot file size (>1000 bytes) before processing
- Template matching threshold of 0.8 may need adjustment for UI changes
- Color-based unit matching sensitive to lighting - test MSE < 2000 threshold
- Check BlueStacks resolution matches expected coordinates (1600x900)

### Threading & GUI Synchronization
**Problem**: GUI freezes or bot stops responding
```python
# Proper threading pattern
def update_text(self, *args):
    # Thread-safe GUI updates only
    tbox.config(state=NORMAL)
    tbox.delete(1.0, END)
    tbox.insert(END, text)
    tbox.config(state=DISABLED)
    self.root.update_idletasks()  # Critical for thread safety
```

**Solutions**:
- Always use `threading.Event` for cross-thread communication
- GUI updates must be thread-safe with `root.update_idletasks()`
- Bot stop mechanisms require cooperative thread termination via `bot.bot_stop = True`
- Avoid blocking operations in main GUI thread

### Configuration & Unit Selection Issues
**Problem**: Units not recognized or config changes not applied
```python
# Unit selection validation
def select_units(units):
    if not os.path.isdir('units'):
        os.mkdir('units')
    
    valid_count = 0
    for new_unit in units:
        source_path = f'all_units/{new_unit}'
        if os.path.exists(source_path):
            cv2.imwrite(f'units/{new_unit}', cv2.imread(source_path))
            valid_count += 1
        else:
            print(f'{new_unit} not found in all_units/')
    
    return valid_count > 4  # Need at least 5 units
```

**Solutions**:
- Verify unit images exist in `all_units/` before copying to `units/`
- Check config.ini syntax for units list (comma-separated, no .png extension)
- Ensure GUI config updates write to file: `self.config.write(configfile)`
- Test unit color analysis for new units before adding to deck

### Performance & Memory Issues
**Problem**: Bot becomes slow or memory usage increases over time
```python
# Memory management in long-running loops
def combat_loop(bot, grid_df, mana_targets, user_target):
    # Explicit cleanup of large DataFrames
    if grid_df is not None:
        del grid_df
    
    # Limit screenshot history
    screenshot_path = f'bot_feed_{bot.bot_id}.png'
    if os.path.exists(screenshot_path):
        # Only keep current screenshot
        pass
    
    # Force garbage collection periodically
    import gc
    if combat_count % 100 == 0:
        gc.collect()
```

**Solutions**:
- Screenshots accumulate - clean old files periodically
- Pandas DataFrames in grid analysis can consume memory - explicit cleanup
- Thread objects may not be garbage collected - use proper `thread.join()`
- Monitor memory usage during long bot runs

### Game State Recovery & Error Handling
**Problem**: Bot gets stuck in unknown states or fails to navigate
```python
# Robust state recovery pattern
def battle_screen(self, start=False, pve=True, floor=5):
    max_attempts = 3
    for attempt in range(max_attempts):
        df = self.get_current_icons(available=True)
        
        if df.empty:
            self.logger.warning(f'No icons detected, attempt {attempt+1}')
            self.getScreen()  # Force new screenshot
            time.sleep(1)
            continue
            
        # Try to identify current state
        if self._detect_known_state(df):
            return df, state
    
    # Last resort - force restart
    self.logger.error('Unable to determine game state, restarting')
    self.restart_RR()
```

**Solutions**:
- Implement multiple attempts for state detection before giving up
- Use forced navigation (`KEYCODE_BACK`) when state is unknown
- Game restart mechanisms for completely stuck states
- Log all state transitions for debugging patterns

## File Organization Logic & Detailed Structure

### Core Source Files (`Src/`)
- **`bot_core.py`**: Foundation class with ADB communication, screenshot management, basic actions
  - Device connection handling with fallbacks
  - Screenshot capture with 3-tier fallback system
  - Touch/swipe commands with human-like timing
  - Grid coordinate mapping and game state navigation

- **`bot_handler.py`**: High-level game logic and main bot loop
  - State machine implementation for menu navigation
  - Combat strategy and unit merging algorithms  
  - Ad watching automation and resource management
  - Configuration loading and unit selection systems

- **`bot_perception.py`**: Computer vision and machine learning components
  - Template matching for UI element detection
  - Color-based unit recognition with MSE distance calculations
  - ML rank classification using sklearn LogisticRegression
  - Grid analysis with pandas DataFrames and age tracking

- **`gui.py`**: Tkinter interface with threading coordination
  - Real-time combat display and unit statistics
  - Configuration interface for mana targets and floor selection
  - Log feed integration with custom logger handlers
  - Thread-safe GUI updates and bot control buttons

- **`bot_logger.py`**: Logging system integration
- **`port_scan.py`**: Android device discovery and connection utilities

### Image Assets & Recognition Data
- **`icons/`**: UI element templates for game state detection
  - PNG files used for template matching (threshold 0.8)
  - Critical files: `fighting.png`, `home_screen.png`, `battle_icon.png`
  - Button detection: `back_button.png`, `0cont_button.png`, `1quit.png`

- **`all_units/`**: Master library of all available unit images
  - Complete collection of unit types with consistent naming
  - Source for unit selection - files copied to `units/` directory
  - Color analysis reference for unit recognition algorithms

- **`units/`**: Active unit deck (copied from `all_units/`)
  - Dynamic directory updated based on config.ini selection
  - Used by `bot_perception.py` for color matching reference
  - Cleared and repopulated when unit selection changes

- **`OCR_inputs/`**: Grid slot screenshots for analysis
  - 15 files named `icon_0.png` through `icon_14.png`
  - Represents 3x5 combat grid captured during gameplay
  - Used for unit recognition and rank classification

### Configuration & Data Files
- **`config.ini`**: Central configuration with sections:
  ```ini
  [bot]
  floor = 7                                    # Target dungeon floor
  mana_level = 1,2,3,4,5                      # Card upgrade sequence
  units = demo, boreas, robot, dryad, franky_stein  # Active unit deck
  dps_unit = boreas                            # Primary damage dealer
  pve = False                                  # PvE vs PvP mode
  require_shaman = False                       # Opponent requirement
  ```

- **`rank_model.pkl`**: Trained sklearn model for unit rank classification
- **`requirements.txt`**: Python 3.13 compatible dependency list
- **`RR_bot.log`**: Runtime log file with bot actions and debug info

### Entry Points & Launchers
- **`launch_gui.bat`**: Windows batch script for GUI mode
  ```batch
  @echo off
  call .bot_env\Scripts\activate.bat
  python Src\gui.py
  pause
  ```

- **`install.bat`**: Dependency installation script
- **`RR_bot.ipynb`**: Jupyter notebook for development and RL experimentation

### Development & Debug Files
- **`bot_feed_emulator-5554.png`**: Latest screenshot from Android device
  - Critical for debugging computer vision issues
  - File size should be >1000 bytes for valid screenshots
  - Updated continuously during bot operation

- **`calculon.ico`**: GUI window icon
- **`README.md`**: Comprehensive project documentation with RL architecture

### Directory Structure Conventions
```
Rush-Royale-Bot/
├── Src/                    # Core bot implementation
├── icons/                  # UI template images
├── all_units/              # Master unit library
├── units/                  # Active deck selection
├── OCR_inputs/             # Grid analysis screenshots
├── config/                 # Alternative configurations
├── scripts/                # Additional tools and launchers
└── .github/                # Repository metadata and AI instructions
```

### Critical File Dependencies
1. **Screenshot Pipeline**: `bot_core.py` → `bot_feed_*.png` → `icons/` matching
2. **Unit Recognition**: `all_units/` → `units/` → `OCR_inputs/` → `rank_model.pkl`
3. **Configuration Flow**: `config.ini` → `gui.py` → `bot_handler.py` → `bot_core.py`
4. **Threading Communication**: `gui.py` ↔ `bot_handler.py` via `threading.Event`

When modifying this codebase, prioritize:
1. **Computer vision reliability** - screenshot quality and template matching accuracy
2. **ADB connection stability** - device communication and fallback mechanisms  
3. **Thread safety** - proper coordination between GUI and bot execution
4. **Configuration integrity** - consistent state between GUI, config files, and runtime behavior

The architecture is designed for reliability in a Windows + BlueStacks environment, with extensive fallback mechanisms for Android device communication and computer vision challenges.
