# Core Modules

Detailed documentation for the main source modules in `Src/`.

---

## bot_core.py

The central `Bot` class handling ADB communication, screen capture, and game interaction.

### Class: `Bot`

Main bot controller that interfaces with an Android device via ADB.

#### Constructor

```python
Bot(device: str | None = None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str \| None` | ADB device address (e.g., `127.0.0.1:5555`). Auto-detected if `None`. |

**Initialization Steps:**
1. Connects to device via `adbutils` (preferred) or fallback ADB executable
2. Launches Rush Royale (`com.my.defense`)
3. Takes initial screenshot
4. Starts `scrcpy` client for low-latency touch input

#### Core Methods

##### `shell(cmd: str)`
Execute an ADB shell command on the connected device.

```python
bot.shell("input tap 450 1360")
```

##### `click(x: int, y: int, delay_mult: float = 1)`
Tap at screen coordinates. Uses `scrcpy` if available, otherwise ADB input.

```python
bot.click(450, 1360)  # Tap spawn button
bot.click(200, 300, delay_mult=2)  # Tap with longer delay
```

##### `click_button(pos)`
Click a button with offset and extended delay. Used for UI buttons.

```python
bot.click_button((100, 200))  # Adds +10px offset, 1s delay
```

##### `swipe(start, end)`
Drag from one grid position to another (for merging units).

```python
bot.swipe((0, 0), (1, 0))  # Merge grid[0,0] → grid[1,0]
```

##### `key_input(key: int)`
Send a key event (e.g., back button).

```python
bot.key_input(4)  # KEYCODE_BACK
```

##### `getScreen()`
Capture device screen and store in `self.screenRGB` (BGR format).

Tries methods in order:
1. `adbutils.screenshot()` – Fastest, memory-only
2. ADB `exec-out screencap` – Writes to file

##### `crop_img(x, y, dx, dy, name)`
Crop a region from the latest screenshot and save to file.

```python
bot.crop_img(100, 200, 50, 50, "icon.png")
```

##### `get_current_icons(new: bool = True, available: bool = False, icon_list = None) -> pd.DataFrame`
Detect which icons are visible on screen using template matching.

**Returns:** DataFrame with columns `['icon', 'available', 'pos [X,Y]']`

```python
icons_df = bot.get_current_icons()
if (icons_df['icon'] == 'battle_icon.png').any():
    print("Battle button visible")
```

##### `scan_grid(new: bool = False)`
Scan the 3×5 battle grid and save cropped unit images to `OCR_inputs/`.

##### `getXYByImage(target: str, new: bool = True)`
Find a specific icon on screen. Returns `[x, y]` or `[0, 0]` if not found.

Valid targets: `battle_icon`, `pvp_button`, `back_button`, `cont_button`, `fighting`

##### `restart_game(quick_disconnect: bool = False)`
Force restart Rush Royale app or spam reconnects to abandon match.

##### `unit_update_capture_missing_units()`
Interactive mode to capture screenshots of missing unit icons. Prompts user for unit names and saves to `cv-images/all_units/missing_units/`.

#### Combat Methods

##### `try_merge(prev_grid, merge_target) -> tuple`
Analyze grid and perform merge operations targeting the specified unit.

**Returns:** `(grid_df, unit_series, merge_series, df_groups, info)`

##### `mana_level(targets, hero_power: bool = True)`
Click mana upgrade buttons for specified card positions.

```python
bot.mana_level([1, 3, 5])  # Upgrade cards 1, 3, 5
```

##### `battle_screen(start: bool, pve: bool = True, floor: int = 5)`
Navigate menu screens to start or detect battle state.

---

## bot_perception.py

Computer vision functions for unit and rank recognition.

### Constants

| Name | Description |
|------|-------------|
| `REPO_ROOT` | Project root directory |
| `RANK_MODEL_PATH` | Path to `rank_model.pkl` |
| `OCR_INPUTS_DIR` | Directory for captured grid cells |
| `ML_INPUTS_DIR` | Preprocessed training images |

### Functions

#### `get_color(filename, crop=False) -> np.ndarray`
Extract the 5 most common pixel colors from an image.

```python
colors = get_color("unit.png", crop=True)  # Shape: (5, 3)
```

#### `match_unit(filename, ref_colors, ref_units) -> list`
Identify a unit by comparing colors to reference templates.

**Returns:** `[unit_name, mse_score]`

```python
unit, score = match_unit("cell.png", ref_colors, ref_units)
if score < 2000:
    print(f"Detected: {unit}")
```

#### `grid_status(names, prev_grid=None) -> pd.DataFrame`
Analyze all 15 grid cells and return unit/rank information.

**Columns:**
- `grid_pos`: [row, col] position
- `unit`: Matched unit filename
- `u_prob`: Match confidence (MSE)
- `rank`: Detected rank (0-7)
- `r_prob`: Rank probability
- `Age`: Frames since last change

#### `match_rank(filename) -> tuple[int, float]`
Predict unit rank using the trained LogisticRegression model.

**Returns:** `(rank, probability)`

```python
rank, prob = match_rank("cell_5.png")
print(f"Rank {rank} with {prob:.1%} confidence")
```

#### `position_filter(grid_df, key_target) -> int`
Find the highest-rank `knight_statue` adjacent to the DPS unit.

#### `train_rank_model(dataset_dir) -> LogisticRegression`
Train a new rank recognition model on labeled images.

#### `save_rank_model(model, path)`
Serialize trained model to pickle file.

#### `load_dataset(folder) -> tuple[np.ndarray, np.ndarray]`
Load labeled training images from a folder structure.

Supports:
- Flat: `{rank}_input_{id}.png`
- Nested: `{rank}/{id}.png`

---

## bot_handler.py

High-level bot lifecycle, configuration, and game loop.

### Functions

#### `select_units(units: list[str]) -> bool`
Copy selected unit templates from `cv-images/all_units/` to `cv-images/units/`.

```python
success = select_units(['demon_hunter.png', 'dryad.png', 'harlequin.png'])
```

#### `start_bot_class(logger) -> Bot`
Initialize and return a new `Bot` instance.

#### `combat_loop(bot, grid_df, mana_targets, user_target) -> tuple`
Execute one combat frame: mana upgrades, spawns, and merges.

**Returns:** Updated `(grid_df, unit_series, merge_series, df_groups, info)`

#### `bot_loop(bot, info_event)`
Main game loop. Handles:
1. **Unit Update Mode**: Interactive capture if `unit_update=True`
2. **Combat**: Continuous merge/upgrade cycle
3. **Navigation**: Auto-restart on timeout or shaman requirement
4. **Ad Watching**: After matches complete

#### `check_adb_connection(logger) -> bool`
Verify ADB can communicate with at least one device.

#### `download(url, filename)`
Download a file with progress bar (used for scrcpy installation).

---

## gui.py

Modern CustomTkinter-based graphical interface for bot control.

### Architecture

The GUI uses CustomTkinter for a modern, dark-mode compatible interface with:
- **Responsive layout** via grid-based design
- **System theme detection** (Dark/Light mode)
- **Tabbed content area** for organized information
- **Left sidebar** for controls (follows F-pattern UX)

### Class: `RushBotApp`

Main application window inheriting from `ctk.CTk`.

#### Key Components

| Component | Purpose |
|-----------|---------|
| `SidebarFrame` | Controls, settings, mode toggles |
| `ContentFrame` | Tabbed area with combat info, logs, about |
| `CombatInfoFrame` | Grid status and unit series display |
| `LogFrame` | Scrollable log output |

#### Methods

##### `start_command()`
Save settings to `config.ini` and launch bot in separate thread.

##### `stop_bot()`
Signal bot to stop and update button states.

##### `leave_game()`
Trigger quick disconnect from current dungeon.

##### `_update_config()`
Write current GUI values to `config.ini`.

##### `_update_display(...)`
Update combat info textboxes with latest bot data.

### Class: `SidebarFrame`

Left sidebar with all controls.

#### Widgets

| Widget | Type | Purpose |
|--------|------|---------|
| Start Button | `CTkButton` | Begin bot automation |
| Stop Button | `CTkButton` | Stop bot safely |
| Quit Floor | `CTkButton` | Leave current game |
| PvE Switch | `CTkSwitch` | Toggle PvE/PvP mode |
| Unit Update Switch | `CTkSwitch` | Enable capture mode |
| Mana Checkboxes | `CTkCheckBox` | Select upgrade targets (1-5) |
| Floor Entry | `CTkEntry` | Set dungeon floor number |

### Class: `ContentFrame`

Tabbed content area with three tabs:
- **📊 Combat Info**: Grid status, unit/merge series
- **📝 Log**: Scrollable log output
- **ℹ️ About**: Application information

### Theming

```python
ctk.set_appearance_mode("System")  # Auto dark/light
ctk.set_default_color_theme("blue")  # Color scheme
```

Custom color palette defined in `COLORS` dict for consistent styling.

### Legacy GUI

The original Tkinter GUI is preserved as `gui_legacy.py` for reference.

---

## port_scan.py

ADB device discovery utilities.

### Functions

#### `get_device() -> str | None`
Scan common emulator ports and return the first connected device address.

**Checked Ports:**
- `5555-5585` (LDPlayer, NoxPlayer, BlueStacks)
- `21503, 62001, 62025` (Alternative emulator ports)

```python
device = port_scan.get_device()
if device:
    bot = Bot(device=device)
```

---

## scrcpy_client.py / scrcpy/__init__.py

Vendored scrcpy client shim for touch input.

### Purpose

Wraps the `scrcpy-client` library to provide low-latency touch input via scrcpy protocol instead of ADB input commands.

### Usage

```python
from scrcpy import Client, const

client = Client(device="127.0.0.1:5555")
client.start(threaded=True)
client.control.touch(x, y, const.ACTION_DOWN)
client.control.touch(x, y, const.ACTION_UP)
```

### Fallback

If scrcpy is unavailable, the bot falls back to `adb shell input tap`.
