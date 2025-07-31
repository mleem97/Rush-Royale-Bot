# Rush Royale Bot - API Reference

Complete API documentation for developers working with the Rush Royale Bot codebase.

## Table of Contents

1. [Core API](#core-api)
2. [Module APIs](#module-apis)
3. [Interface APIs](#interface-apis) 
4. [Configuration API](#configuration-api)
5. [Utility Functions](#utility-functions)
6. [Error Handling](#error-handling)
7. [Examples](#examples)

## Core API

### RushRoyaleBot Class

Main bot controller class that coordinates all bot operations.

```python
class RushRoyaleBot:
    """
    Main Rush Royale Bot controller.
    
    This class provides the primary interface for bot operations including
    device management, battle automation, and game state monitoring.
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        Initialize the bot with configuration.
        
        Args:
            config_path: Path to configuration file
            
        Raises:
            ConfigurationError: If config file is invalid
            InitializationError: If core components fail to initialize
        """
```

#### Device Management Methods

```python
def connect_device(self, device_id: Optional[str] = None) -> bool:
    """
    Connect to Android device via ADB.
    
    Args:
        device_id: Specific device ID to connect to (optional)
        
    Returns:
        bool: True if connection successful, False otherwise
        
    Raises:
        DeviceConnectionError: If ADB connection fails
        DeviceNotFoundError: If no compatible devices found
    """

def disconnect_device(self) -> bool:
    """
    Disconnect from current device.
    
    Returns:
        bool: True if disconnection successful
    """

def is_connected(self) -> bool:
    """
    Check if device is currently connected.
    
    Returns:
        bool: True if device is connected and responsive
    """

def get_device_info(self) -> Dict[str, Any]:
    """
    Get information about connected device.
    
    Returns:
        Dict containing device information:
        - model: Device model name
        - android_version: Android OS version
        - screen_resolution: Screen dimensions (width, height)
        - density: Screen density (DPI)
        - battery_level: Current battery percentage
        
    Raises:
        DeviceNotConnectedError: If no device is connected
    """
```

#### Screen Capture Methods

```python
def get_screenshot(self) -> Optional[np.ndarray]:
    """
    Capture current device screen.
    
    Returns:
        numpy.ndarray: Screenshot image in BGR format, or None if failed
        
    Raises:
        ScreenCaptureError: If screenshot capture fails
        DeviceNotConnectedError: If device is not connected
    """

def get_screenshot_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
    """
    Capture specific region of screen.
    
    Args:
        x: Left coordinate
        y: Top coordinate  
        width: Region width
        height: Region height
        
    Returns:
        numpy.ndarray: Cropped screenshot or None if failed
    """
```

#### Game State Methods

```python
def detect_game_state(self) -> GameState:
    """
    Detect current game state.
    
    Returns:
        GameState: Current game state information including:
        - current_screen: Current screen/menu
        - in_battle: Whether currently in battle
        - battle_type: Type of battle (pve/pvp)
        - chapter: Current chapter (if applicable)
        - confidence: Detection confidence (0.0-1.0)
    """

def get_battle_grid(self) -> Optional[pd.DataFrame]:
    """
    Extract and analyze battle grid.
    
    Returns:
        pandas.DataFrame: Grid analysis with columns:
        - position_index: Grid position (0-14)
        - grid_x, grid_y: Grid coordinates
        - unit: Detected unit name
        - confidence: Recognition confidence
        - rank: Unit rank/level
        
    Returns None if not in battle or grid detection fails
    """
```

#### Battle Control Methods

```python
def start_pve_battle(self, chapter: int = 1, timeout: float = 300.0) -> bool:
    """
    Start PvE battle in specified chapter.
    
    Args:
        chapter: Chapter number (1-5)
        timeout: Maximum time to wait for battle start
        
    Returns:
        bool: True if battle started successfully
        
    Raises:
        NavigationError: If unable to navigate to battle
        TimeoutError: If battle doesn't start within timeout
    """

def wait_for_battle_completion(self, timeout: float = 600.0) -> bool:
    """
    Wait for current battle to complete.
    
    Args:
        timeout: Maximum time to wait for battle completion
        
    Returns:
        bool: True if battle completed successfully, False if failed/timeout
    """

def perform_merge_action(self, pos1: int, pos2: int) -> bool:
    """
    Merge units at specified grid positions.
    
    Args:
        pos1: First unit position (0-14)
        pos2: Second unit position (0-14)
        
    Returns:
        bool: True if merge action performed successfully
        
    Raises:
        InvalidPositionError: If positions are invalid
        MergeError: If merge operation fails
    """
```

### DeviceManager Class

Handles all device communication and control.

```python
class DeviceManager:
    """
    Manages Android device communication via ADB.
    """
    
    def __init__(self, adb_path: Optional[str] = None):
        """
        Initialize device manager.
        
        Args:
            adb_path: Custom path to ADB executable (optional)
        """

    def find_devices(self) -> List[str]:
        """
        Find all connected Android devices.
        
        Returns:
            List[str]: List of device IDs
        """

    def connect(self, device_id: Optional[str] = None) -> bool:
        """
        Connect to specific device.
        
        Args:
            device_id: Target device ID, or None for first available
            
        Returns:
            bool: Connection success status
        """

    def execute_shell_command(self, command: str) -> Tuple[bool, str]:
        """
        Execute shell command on device.
        
        Args:
            command: Shell command to execute
            
        Returns:
            Tuple of (success: bool, output: str)
        """

    def click(self, x: int, y: int) -> bool:
        """
        Perform touch click at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: True if click performed successfully
        """

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """
        Perform swipe gesture.
        """
```

### PerceptionSystem Class

Computer vision and image analysis.

```python
class PerceptionSystem:
    """
    Handles computer vision and image analysis tasks.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize perception system.
        
        Args:
            config: Vision configuration parameters
        """

    def find_icon(self, image: np.ndarray, icon_path: str, 
                  threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Find icon in image using template matching.
        
        Args:
            image: Input image to search
            icon_path: Path to icon template
            threshold: Matching confidence threshold
            
        Returns:
            Tuple[int, int]: Icon center coordinates if found, None otherwise
        """

    def extract_colors(self, image: np.ndarray, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from image.
        
        Args:
            image: Input image
            num_colors: Number of dominant colors to extract
            
        Returns:
            List of RGB color tuples
        """

    def detect_grid_positions(self, image: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect battle grid cell positions.
        
        Args:
            image: Battle screen image
            
        Returns:
            List of (x, y) coordinates for each grid cell
        """
```

## Module APIs

### Combat Module

Strategic combat and unit management.

```python
class CombatStrategy:
    """
    Implements combat strategies and unit merge logic.
    """
    
    def __init__(self, strategy_type: str = "balanced"):
        """
        Initialize combat strategy.
        
        Args:
            strategy_type: Strategy type ('aggressive', 'conservative', 'balanced')
        """

    def analyze_battle_state(self, grid_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze current battle state.
        
        Args:
            grid_df: Current grid state dataframe
            
        Returns:
            Dict containing:
            - unit_count: Number of units on board
            - merge_opportunities: Available merge positions
            - strategy_recommendation: Recommended next action
            - threat_level: Current threat assessment
        """

    def find_best_merge(self, grid_df: pd.DataFrame) -> Optional[Tuple[int, int]]:
        """
        Find optimal merge positions.
        
        Args:
            grid_df: Current grid state
            
        Returns:
            Tuple of (pos1, pos2) for best merge, or None if no good merges
        """

    def execute_combat_round(self, bot_instance) -> Dict[str, Any]:
        """
        Execute one round of combat decisions.
        
        Args:
            bot_instance: Main bot instance for actions
            
        Returns:
            Dict containing round results and statistics
        """
```

### Navigation Module

Game navigation and state management.

```python
class NavigationSystem:
    """
    Handles game navigation and state detection.
    """
    
    def detect_current_screen(self, img: Optional[np.ndarray] = None) -> GameState:
        """
        Detect current game screen.
        
        Args:
            img: Screenshot to analyze (optional, will capture if None)
            
        Returns:
            GameState: Current game state information
        """

    def navigate_to_home(self, timeout: float = 10.0) -> bool:
        """
        Navigate to home screen.
        
        Args:
            timeout: Maximum navigation time
            
        Returns:
            bool: True if successfully reached home screen
        """

    def start_battle(self, battle_type: str = "pve", chapter: int = 1, 
                    timeout: float = 30.0) -> bool:
        """
        Start battle of specified type.
        
        Args:
            battle_type: Battle type ('pve' or 'pvp')
            chapter: Chapter number for PvE
            timeout: Maximum time to start battle
            
        Returns:
            bool: True if battle started successfully
        """
```

### Recognition Module

Advanced unit recognition system.

```python
class UnitRecognizer:
    """
    Advanced unit recognition using multiple techniques.
    """
    
    def recognize_unit(self, unit_image: np.ndarray, 
                      position: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """
        Recognize unit from image crop.
        
        Args:
            unit_image: Cropped unit image
            position: Grid position (optional)
            
        Returns:
            Dict containing:
            - unit_name: Recognized unit name
            - confidence: Recognition confidence (0.0-1.0)
            - rank: Unit rank/level
            - position: Grid position
        """

    def recognize_grid_units(self, grid_crops: List[np.ndarray], 
                           positions: List[Tuple[int, int]]) -> pd.DataFrame:
        """
        Recognize all units in grid.
        
        Args:
            grid_crops: List of unit image crops
            positions: List of grid positions
            
        Returns:
            pandas.DataFrame: Recognition results for entire grid
        """

    def update_unit_template(self, unit_name: str, new_image: np.ndarray):
        """
        Update unit template with new image.
        
        Args:
            unit_name: Name of unit to update
            new_image: New template image
        """
```

### Automation Module

High-level automation workflows.

```python
class AutomationEngine:
    """
    High-level automation engine for bot operations.
    """
    
    def start_automation(self, tasks: List[str] = None, 
                        session_config: Dict = None):
        """
        Start automation with specified tasks.
        
        Args:
            tasks: List of task names to execute
            session_config: Session configuration parameters
        """

    def stop_automation(self):
        """Stop automation gracefully."""

    def get_automation_status(self) -> Dict[str, Any]:
        """
        Get current automation status.
        
        Returns:
            Dict containing:
            - running: Whether automation is active
            - current_task: Currently executing task
            - battles_completed: Number of battles completed
            - session_duration: Current session duration
        """

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get performance metrics and analysis.
        
        Returns:
            Dict containing performance statistics and metrics
        """
```

### Debug Module

Debugging and monitoring system.

```python
class DebugSystem:
    """
    Comprehensive debugging system for bot operations.
    """
    
    def enable(self):
        """Enable debug mode."""

    def log_event(self, event_type: str, operation: str, 
                 details: Dict[str, Any] = None, success: bool = True):
        """
        Log debug event.
        
        Args:
            event_type: Type of event (e.g., 'ACTION', 'RECOGNITION')
            operation: Operation name
            details: Additional event details
            success: Whether operation was successful
        """

    def debug_screenshot(self, img: np.ndarray, filename: str = None, 
                        operation: str = "screenshot") -> str:
        """
        Save debug screenshot.
        
        Args:
            img: Image to save
            filename: Custom filename (optional)
            operation: Operation name for logging
            
        Returns:
            str: Path to saved screenshot
        """

    def get_summary(self) -> Dict:
        """
        Get debug session summary.
        
        Returns:
            Dict containing session statistics and metrics
        """
```

## Interface APIs

### GUI Interface

Modern graphical interface using CustomTkinter.

```python
class ModernBotGUI:
    """
    Modern GUI interface for Rush Royale Bot.
    """
    
    def __init__(self):
        """Initialize GUI components."""

    def run(self):
        """Start the GUI application."""

    def connect_device(self):
        """Connect to Android device through GUI."""

    def start_automation(self, config: Dict[str, Any]):
        """
        Start automation with GUI configuration.
        
        Args:
            config: Automation configuration from GUI settings
        """
```

### CLI Interface

Command line interface for bot operations.

```python
class BotCLI:
    """
    Command Line Interface for Rush Royale Bot.
    """
    
    def run_single_battle(self, chapter: int = 1, battle_type: str = "pve") -> bool:
        """
        Run single battle via CLI.
        
        Args:
            chapter: Chapter number
            battle_type: Battle type
            
        Returns:
            bool: Battle success status
        """

    def run_automation(self, chapter: int = 1, max_battles: int = 10, 
                      battle_type: str = "pve") -> bool:
        """
        Run automation via CLI.
        
        Args:
            chapter: Chapter number
            max_battles: Maximum battles to run
            battle_type: Battle type
            
        Returns:
            bool: Automation success status
        """
```

## Configuration API

### ConfigManager Class

Configuration management system.

```python
class ConfigManager:
    """
    Manages bot configuration from multiple sources.
    """
    
    def __init__(self, config_path: str = "config.ini"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to main configuration file
        """

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """

    def set(self, section: str, key: str, value: Any):
        """
        Set configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """

    def load_user_config(self, config_path: str):
        """
        Load user-specific configuration.
        
        Args:
            config_path: Path to user configuration file
        """

    def save_config(self, config_path: str = None):
        """
        Save current configuration to file.
        
        Args:
            config_path: Output file path (optional)
        """
```

## Utility Functions

### Image Processing Utilities

```python
def resize_image(image: np.ndarray, target_size: Tuple[int, int], 
                maintain_aspect: bool = True) -> np.ndarray:
    """
    Resize image to target dimensions.
    
    Args:
        image: Input image
        target_size: Target (width, height)
        maintain_aspect: Whether to maintain aspect ratio
        
    Returns:
        Resized image
    """

def crop_image_region(image: np.ndarray, x: int, y: int, 
                     width: int, height: int) -> np.ndarray:
    """
    Crop rectangular region from image.
    
    Args:
        image: Input image
        x, y: Top-left coordinates
        width, height: Region dimensions
        
    Returns:
        Cropped image region
    """

def enhance_image_quality(image: np.ndarray) -> np.ndarray:
    """
    Enhance image quality for better recognition.
    
    Args:
        image: Input image
        
    Returns:
        Enhanced image
    """
```

### Coordinate Utilities

```python
def grid_position_to_coordinates(position: int, grid_size: Tuple[int, int]) -> Tuple[int, int]:
    """
    Convert grid position to screen coordinates.
    
    Args:
        position: Grid position (0-14 for 3x5 grid)
        grid_size: Grid dimensions (width, height)
        
    Returns:
        Tuple of (x, y) screen coordinates
    """

def coordinates_to_grid_position(x: int, y: int, grid_bounds: Dict) -> int:
    """
    Convert screen coordinates to grid position.
    
    Args:
        x, y: Screen coordinates
        grid_bounds: Grid boundary information
        
    Returns:
        Grid position index
    """
```

### Time and Performance Utilities

```python
def measure_execution_time(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function with timing
    """

def wait_with_timeout(condition: Callable, timeout: float = 10.0, 
                     check_interval: float = 0.5) -> bool:
    """
    Wait for condition with timeout.
    
    Args:
        condition: Condition function returning bool
        timeout: Maximum wait time
        check_interval: How often to check condition
        
    Returns:
        bool: True if condition met, False if timeout
    """
```

## Error Handling

### Exception Classes

```python
class BotError(Exception):
    """Base exception for bot-related errors."""

class DeviceConnectionError(BotError):
    """Raised when device connection fails."""

class ScreenCaptureError(BotError):
    """Raised when screen capture fails."""

class NavigationError(BotError):
    """Raised when game navigation fails."""

class RecognitionError(BotError):
    """Raised when unit recognition fails."""

class ConfigurationError(BotError):
    """Raised when configuration is invalid."""

class AutomationError(BotError):
    """Raised when automation encounters critical error."""
```

### Error Context Manager

```python
class BotErrorHandler:
    """
    Context manager for comprehensive error handling.
    """
    
    def __init__(self, operation: str, logger: logging.Logger = None):
        """
        Initialize error handler.
        
        Args:
            operation: Name of operation being performed
            logger: Logger instance for error reporting
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle exceptions and provide recovery options."""

# Usage example:
with BotErrorHandler("screenshot_capture") as handler:
    screenshot = bot.get_screenshot()
    # Automatic error handling and recovery
```

## Examples

### Basic Bot Usage

```python
from core.bot import RushRoyaleBot
from modules.automation import AutomationEngine

# Initialize bot
bot = RushRoyaleBot("config.ini")

# Connect to device
if bot.connect_device():
    print("Device connected successfully")
    
    # Get device info
    info = bot.get_device_info()
    print(f"Connected to: {info['model']}")
    
    # Capture screenshot
    screenshot = bot.get_screenshot()
    if screenshot is not None:
        print(f"Screenshot captured: {screenshot.shape}")
    
    # Start single battle
    if bot.start_pve_battle(chapter=3):
        print("Battle started")
        
        # Wait for completion
        if bot.wait_for_battle_completion():
            print("Battle completed successfully")
    
    bot.disconnect_device()
```

### Automation Example

```python
from core.bot import RushRoyaleBot
from modules.automation import AutomationEngine

# Initialize components
bot = RushRoyaleBot()
automation = AutomationEngine(bot)

# Connect and configure
if bot.connect_device():
    # Configure automation
    session_config = {
        'battle_type': 'pve',
        'chapter': 3
    }
    
    automation.update_settings({
        'max_battles_per_session': 20,
        'auto_collect_rewards': True,
        'energy_management': True
    })
    
    # Start automation
    automation.start_automation(
        tasks=['pve_farming', 'reward_collection'],
        session_config=session_config
    )
    
    # Monitor progress
    while automation.running:
        status = automation.get_automation_status()
        print(f"Battles completed: {status['battles_completed']}")
        time.sleep(10)
```

### Custom Recognition Example

```python
from modules.recognition import UnitRecognizer
import cv2

# Initialize recognizer
recognizer = UnitRecognizer()

# Load custom unit image
unit_image = cv2.imread("custom_unit.png")

# Recognize unit
result = recognizer.recognize_unit(unit_image)
print(f"Recognized: {result['unit_name']} (confidence: {result['confidence']:.2f})")

# Update template
if result['confidence'] > 0.9:
    recognizer.update_unit_template(result['unit_name'], unit_image)
    print("Template updated")
```

### Debug Mode Example

```python
from modules.debug import get_debug_system, enable_debug

# Enable debug mode
enable_debug()
debug_system = get_debug_system()

# Your bot operations here
bot = RushRoyaleBot()
# ... bot operations ...

# Get debug summary
summary = debug_system.get_summary()
print(f"Debug events: {summary['total_events']}")
print(f"Errors: {summary['errors_count']}")

# Export session data
debug_system.export_session_data("debug_session.json")
```

---

For more examples and detailed implementation guides, see the [User Guide](User-Guide.md) and [Technical Guide](Technical-Guide.md).
