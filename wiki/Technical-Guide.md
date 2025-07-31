# Rush Royale Bot - Technical Guide

This technical guide provides in-depth information about the bot's architecture, advanced configuration options, and development details.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Module System](#module-system)
4. [Configuration System](#configuration-system)
5. [Computer Vision Pipeline](#computer-vision-pipeline)
6. [Machine Learning Components](#machine-learning-components)
7. [Device Communication](#device-communication)
8. [Performance Optimization](#performance-optimization)
9. [Development Setup](#development-setup)
10. [Contributing](#contributing)

## Architecture Overview

### System Design

The Rush Royale Bot follows a modular architecture with clear separation of concerns:

```
Rush-Royale-Bot/
├── core/                    # Core bot functionality
│   ├── bot.py              # Main bot controller (refactored from legacy bot_core.py)
│   ├── device.py           # Device management and ADB communication
│   ├── perception.py       # Computer vision and unit recognition
│   ├── logger.py           # Centralized logging system
│   └── config.py           # Configuration management
├── modules/                 # Specialized modules
│   ├── combat.py           # Combat strategies and battle logic
│   ├── navigation.py       # Game navigation and UI interaction
│   ├── recognition.py      # Advanced unit recognition algorithms
│   ├── automation.py       # Automation workflows and macros
│   └── debug.py            # Debug utilities and monitoring
├── interface/               # User interfaces
│   ├── gui.py              # Modern GUI (refactored from legacy Src/gui.py)
│   └── cli.py              # Command line interface
├── tools/                   # Development utilities (organized from root)
│   ├── test_dependencies.py    # System verification
│   ├── device_manager.py       # ADB device management
│   ├── health_check.py         # Comprehensive diagnostics
│   └── version_info.py         # Version information
└── wiki/                   # Complete documentation system
    ├── Technical-Guide.md      # This file - technical details
    ├── User-Guide.md          # User documentation
    ├── API-Reference.md       # API documentation  
    └── CHANGELOG.md           # Version history
```

### Design Principles

1. **Modularity**: Each component has a single responsibility
2. **Separation of Concerns**: Clear boundaries between layers
3. **Maintainability**: Consistent code structure and naming
4. **Extensibility**: Easy to add new features and modules
5. **Backward Compatibility**: Legacy Src/ components still available during transition

### Migration Status (v2.1.0)

The bot is currently in a **hybrid state** during the architectural transition:

**✅ New Modular Structure (Active)**
- `core/` - Essential bot functionality (primary)
- `modules/` - Specialized components (primary)  
- `interface/` - User interfaces (primary)

**🔄 Legacy Structure (Transitional)**
- `Src/` - Original implementation (backup/compatibility)
  - Some components still reference legacy files
  - Gradual migration to new modular structure
  - Maintained for backward compatibility

**🎯 Migration Priority**
- New development uses modular structure
- Legacy components gradually refactored
- Both structures work during transition period
2. **Extensibility**: Easy to add new features and strategies
3. **Maintainability**: Clean code with comprehensive documentation
4. **Performance**: Optimized for real-time game interaction
5. **Reliability**: Robust error handling and recovery

## Core Components

### Bot Core (core/bot.py)

The main `RushRoyaleBot` class orchestrates all bot operations:

```python
class RushRoyaleBot:
    def __init__(self, config_path: str = "config.ini"):
        # Initialize all subsystems
        self.device_manager = DeviceManager()
        self.perception_system = PerceptionSystem()
        self.logger = BotLogger()
        self.config = ConfigManager(config_path)
```

**Key Features:**
- Device connection management
- Screen capture and analysis
- Battle state detection
- Unit grid recognition
- Strategic decision making

### Device Manager (core/device.py)

Handles all Android device communication:

```python
class DeviceManager:
    def __init__(self):
        self.adb_path = self._find_adb()
        self.device_id = None
        self.screen_size = None
```

**Capabilities:**
- ADB communication
- Screen capture via scrcpy
- Touch input simulation
- Device information retrieval
- Connection stability monitoring

### Perception System (core/perception.py)

Computer vision and image analysis:

```python
class PerceptionSystem:
    def __init__(self):
        self.template_matcher = TemplateMatcher()
        self.color_analyzer = ColorAnalyzer()
        self.grid_detector = GridDetector()
```

**Features:**
- Template matching
- Color-based recognition
- Grid detection and analysis
- Image preprocessing
- Confidence scoring

## Module System

### Combat Module (modules/combat.py)

Implements battle strategies and unit management:

```python
class CombatStrategy:
    def __init__(self, difficulty="normal"):
        self.merge_strategy = self._load_strategy(difficulty)
        self.unit_priorities = self._load_priorities()
```

**Strategies:**
- **Aggressive**: Fast merging, high risk/reward
- **Conservative**: Safe merging, stable progression
- **Adaptive**: Dynamic strategy based on game state
- **Custom**: User-defined merge patterns

### Navigation Module (modules/navigation.py)

Game interface navigation and state management:

```python
class NavigationSystem:
    def __init__(self, device_manager, perception_system):
        self.device = device_manager
        self.perception = perception_system
        self.current_state = GameState()
```

**Functions:**
- Menu navigation
- Battle initiation
- Reward collection
- Error state recovery
- Screen state detection

### Recognition Module (modules/recognition.py)

Advanced unit recognition using multiple techniques:

```python
class UnitRecognizer:
    def __init__(self):
        self.template_matcher = AdvancedTemplateMatcher()
        self.ml_classifier = MLUnitClassifier()
        self.color_analyzer = ColorAnalyzer()
```

**Recognition Methods:**
1. **Template Matching**: OpenCV-based pattern matching
2. **Machine Learning**: Trained classifier for complex cases
3. **Color Analysis**: Dominant color recognition
4. **Feature Matching**: SIFT/ORB feature detection
5. **Hybrid Approach**: Combination of all methods

## Configuration System

### Configuration Hierarchy

The bot uses a layered configuration system:

1. **Default Settings**: Built-in defaults
2. **Global Config**: `config.ini` file
3. **User Config**: User-specific overrides
4. **Runtime Config**: Dynamic adjustments

### Configuration Files

#### Main Configuration (config.ini)

```ini
[bot]
# Core bot settings
default_chapter = 3
battle_timeout = 300
max_retries = 3
screenshot_interval = 1.0

[recognition]
# Computer vision settings
template_threshold = 0.7
color_tolerance = 30
ml_confidence_threshold = 0.8
enable_hybrid_recognition = true

[automation]
# Automation behavior
max_battles_per_session = 50
session_timeout = 3600
auto_collect_rewards = true
energy_management = true
adaptive_timing = true

[performance]
# Performance optimization
max_cpu_usage = 80
memory_limit_mb = 1024
screenshot_compression = 0.8
parallel_processing = true

[debug]
# Debug and logging
log_level = INFO
save_debug_images = false
performance_profiling = false
error_recovery_attempts = 3
```

#### Device-Specific Configuration

```json
{
  "device_profiles": {
    "samsung_galaxy": {
      "screen_density": 560,
      "click_offset": [0, 0],
      "screenshot_method": "scrcpy",
      "performance_mode": "high"
    },
    "pixel_phone": {
      "screen_density": 440,
      "click_offset": [2, -1],
      "screenshot_method": "adb",
      "performance_mode": "balanced"
    }
  }
}
```

## Computer Vision Pipeline

### Image Processing Workflow

1. **Screen Capture**
   ```python
   def capture_screen(self) -> np.ndarray:
       # Capture using scrcpy or ADB
       raw_image = self.device.get_screenshot()
       
       # Preprocessing
       processed = self.preprocess_image(raw_image)
       
       return processed
   ```

2. **Preprocessing**
   ```python
   def preprocess_image(self, image: np.ndarray) -> np.ndarray:
       # Resize to standard dimensions
       resized = cv2.resize(image, (720, 1280))
       
       # Color space conversion
       if self.config.use_hsv:
           converted = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
       else:
           converted = resized
       
       # Noise reduction
       denoised = cv2.bilateralFilter(converted, 9, 75, 75)
       
       return denoised
   ```

3. **Grid Detection**
   ```python
   def detect_battle_grid(self, image: np.ndarray) -> List[Tuple[int, int]]:
       # Extract grid region
       grid_region = self.extract_grid_region(image)
       
       # Detect grid cells
       cell_positions = self.detect_grid_cells(grid_region)
       
       # Validate grid structure
       validated_positions = self.validate_grid(cell_positions)
       
       return validated_positions
   ```

4. **Unit Recognition**
   ```python
   def recognize_units(self, grid_crops: List[np.ndarray]) -> List[Dict]:
       results = []
       
       for crop in grid_crops:
           # Multiple recognition methods
           template_result = self.template_matching(crop)
           ml_result = self.ml_classification(crop)
           color_result = self.color_analysis(crop)
           
           # Combine results
           final_result = self.combine_recognition_results(
               template_result, ml_result, color_result
           )
           
           results.append(final_result)
       
       return results
   ```

### Template Matching System

The bot uses a sophisticated template matching system:

```python
class AdvancedTemplateMatcher:
    def __init__(self):
        self.templates = self.load_templates()
        self.methods = [
            cv2.TM_CCOEFF_NORMED,
            cv2.TM_CCORR_NORMED,
            cv2.TM_SQDIFF_NORMED
        ]
    
    def match_template(self, image: np.ndarray, template: np.ndarray) -> float:
        best_score = 0.0
        
        # Try multiple scales
        for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
            scaled_template = cv2.resize(template, None, fx=scale, fy=scale)
            
            # Try multiple methods
            for method in self.methods:
                result = cv2.matchTemplate(image, scaled_template, method)
                score = np.max(result) if method != cv2.TM_SQDIFF_NORMED else 1 - np.min(result)
                
                best_score = max(best_score, score)
        
        return best_score
```

## Machine Learning Components

### Unit Classification Model

The bot includes a trained machine learning model for unit recognition:

```python
class MLUnitClassifier:
    def __init__(self, model_path: str = "rank_model.pkl"):
        self.model = joblib.load(model_path)
        self.scaler = StandardScaler()
        self.feature_extractor = FeatureExtractor()
    
    def classify_unit(self, image: np.ndarray) -> Tuple[str, float]:
        # Extract features
        features = self.feature_extractor.extract(image)
        
        # Scale features
        scaled_features = self.scaler.transform([features])
        
        # Predict
        prediction = self.model.predict(scaled_features)[0]
        confidence = np.max(self.model.predict_proba(scaled_features)[0])
        
        return prediction, confidence
```

### Feature Extraction

```python
class FeatureExtractor:
    def extract(self, image: np.ndarray) -> List[float]:
        features = []
        
        # Color features
        features.extend(self.extract_color_features(image))
        
        # Texture features
        features.extend(self.extract_texture_features(image))
        
        # Shape features
        features.extend(self.extract_shape_features(image))
        
        # Statistical features
        features.extend(self.extract_statistical_features(image))
        
        return features
    
    def extract_color_features(self, image: np.ndarray) -> List[float]:
        # HSV color histogram
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
        
        # Normalize and flatten
        normalized = cv2.normalize(hist, hist).flatten()
        
        return normalized.tolist()
```

## Device Communication

### ADB Integration

The bot communicates with Android devices using ADB:

```python
class ADBInterface:
    def __init__(self, adb_path: str = None):
        self.adb_path = adb_path or self._find_adb()
        self.device_id = None
    
    def execute_command(self, command: str) -> Tuple[bool, str]:
        try:
            full_command = f"{self.adb_path} {command}"
            result = subprocess.run(
                full_command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            return result.returncode == 0, result.stdout
        
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)
    
    def click(self, x: int, y: int) -> bool:
        command = f"shell input tap {x} {y}"
        success, _ = self.execute_command(command)
        return success
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        command = f"shell input swipe {x1} {y1} {x2} {y2} {duration}"
        success, _ = self.execute_command(command)
        return success
```

### Screen Capture Methods

Multiple screen capture methods for different devices:

```python
class ScreenCapture:
    def __init__(self, method: str = "auto"):
        self.method = method
        self.capture_methods = {
            "scrcpy": self._capture_scrcpy,
            "adb": self._capture_adb,
            "minicap": self._capture_minicap
        }
    
    def capture(self) -> Optional[np.ndarray]:
        if self.method == "auto":
            # Try methods in order of preference
            for method_name in ["scrcpy", "adb", "minicap"]:
                try:
                    result = self.capture_methods[method_name]()
                    if result is not None:
                        return result
                except Exception:
                    continue
            return None
        else:
            return self.capture_methods[self.method]()
    
    def _capture_scrcpy(self) -> Optional[np.ndarray]:
        # Use scrcpy for high-quality, low-latency capture
        # Implementation details...
        pass
    
    def _capture_adb(self) -> Optional[np.ndarray]:
        # Fallback ADB screenshot method
        success, output = self.adb.execute_command("shell screencap -p")
        if success:
            # Convert base64 to image
            image_data = base64.b64decode(output)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        return None
```

## Performance Optimization

### Multi-threading Architecture

The bot uses multiple threads for optimal performance:

```python
class ThreadedBot:
    def __init__(self):
        self.screen_capture_thread = ScreenCaptureThread()
        self.recognition_thread = RecognitionThread()
        self.action_thread = ActionThread()
        self.monitoring_thread = MonitoringThread()
    
    def start(self):
        # Start all threads
        self.screen_capture_thread.start()
        self.recognition_thread.start()
        self.action_thread.start()
        self.monitoring_thread.start()
        
        # Coordinate between threads
        self._coordinate_threads()
```

### Memory Management

Efficient memory usage for long-running sessions:

```python
class MemoryManager:
    def __init__(self, max_memory_mb: int = 1024):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.image_cache = {}
        self.cache_size_limit = 100
    
    def manage_memory(self):
        # Check current memory usage
        current_usage = psutil.Process().memory_info().rss
        
        if current_usage > self.max_memory:
            # Clear caches
            self.clear_image_cache()
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            self.logger.info(f"Memory cleaned: {current_usage / 1024 / 1024:.1f}MB")
```

### Performance Profiling

Built-in performance monitoring:

```python
class PerformanceProfiler:
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation: str):
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str):
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            
            if operation not in self.metrics:
                self.metrics[operation] = []
            
            self.metrics[operation].append(duration)
            
            # Keep only recent measurements
            if len(self.metrics[operation]) > 100:
                self.metrics[operation] = self.metrics[operation][-100:]
    
    def get_performance_report(self) -> Dict[str, Dict[str, float]]:
        report = {}
        
        for operation, durations in self.metrics.items():
            report[operation] = {
                "avg": np.mean(durations),
                "max": np.max(durations),
                "min": np.min(durations),
                "std": np.std(durations),
                "count": len(durations)
            }
        
        return report
```

## Development Setup

### Development Environment

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-repo/rush-royale-bot.git
   cd rush-royale-bot
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Set Up Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

### Development Dependencies

Additional tools for development:

```txt
# requirements-dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
black>=22.0.0
flake8>=4.0.0
mypy>=0.950
pre-commit>=2.17.0
sphinx>=4.5.0
jupyter>=1.0.0
matplotlib>=3.5.0
seaborn>=0.11.0
```

### Testing Framework

Comprehensive test suite:

```python
# tests/test_bot_core.py
import pytest
from unittest.mock import Mock, patch
from core.bot import RushRoyaleBot

class TestRushRoyaleBot:
    @pytest.fixture
    def bot(self):
        with patch('core.bot.DeviceManager'):
            return RushRoyaleBot()
    
    def test_initialization(self, bot):
        assert bot.device_manager is not None
        assert bot.perception_system is not None
        assert bot.logger is not None
    
    def test_device_connection(self, bot):
        bot.device_manager.connect.return_value = True
        assert bot.connect_device() == True
    
    @patch('core.bot.cv2.imread')
    def test_screenshot_capture(self, mock_imread, bot):
        mock_imread.return_value = Mock()
        screenshot = bot.get_screenshot()
        assert screenshot is not None
```

### Code Quality Standards

The project follows strict code quality standards:

1. **Code Formatting**: Black formatter
2. **Linting**: Flake8 with custom rules
3. **Type Checking**: MyPy for static type analysis
4. **Testing**: PyTest with >90% coverage requirement
5. **Documentation**: Comprehensive docstrings

### Build and Deployment

Automated build process:

```bash
# Run tests
pytest tests/ --cov=. --cov-report=html

# Code formatting
black .

# Linting
flake8 .

# Type checking
mypy .

# Build documentation
sphinx-build -b html docs/ docs/_build/
```

## Contributing

### Contribution Guidelines

1. **Fork the Repository**
2. **Create Feature Branch**: `git checkout -b feature/new-feature`
3. **Make Changes**: Follow code standards
4. **Add Tests**: Ensure >90% test coverage
5. **Update Documentation**: Include relevant docs
6. **Submit Pull Request**: Detailed description of changes

### Development Workflow

```bash
# Start development
git checkout -b feature/my-feature

# Make changes and test
python -m pytest
black .
flake8 .

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-feature
```

### Code Review Process

All contributions go through code review:

1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: Maintainer reviews code quality
3. **Documentation Review**: Ensure docs are updated
4. **Testing**: Verify functionality works as expected
5. **Merge**: After approval, changes are merged

---

For more technical details, see the [API Reference](API-Reference.md) and source code documentation.
