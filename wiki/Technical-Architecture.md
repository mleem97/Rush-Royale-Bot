# Technical Architecture

## System Overview

The Rush Royale Bot is designed as a modular automation system with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Interface │    │   Bot Control   │    │   Game Client   │
│                 │    │                 │    │                 │
│  ┌─────────────┐│    │  ┌─────────────┐│    │ ┌─────────────┐ │
│  │    GUI      ││────│  │  Bot Core   ││────│ │ Bluestacks  │ │
│  │ (Tkinter)   ││    │  │             ││    │ │   Emulator  │ │
│  └─────────────┘│    │  └─────────────┘│    │ └─────────────┘ │
│  ┌─────────────┐│    │  ┌─────────────┐│    │ ┌─────────────┐ │
│  │  Jupyter    ││    │  │ Perception  ││    │ │    Rush     │ │
│  │  Notebook   ││    │  │  (OpenCV)   ││    │ │   Royale    │ │
│  └─────────────┘│    │  └─────────────┘│    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### Bot Core (`Src/bot_core.py`)
- **Primary Responsibility**: Game state management and action execution
- **Key Functions**:
  - `battle_screen()`: Main game loop logic
  - `getScreen()`: Screen capture via scrcpy
  - `click()`, `drag()`: Input injection
  - Device connection and ADB communication

### Perception System (`Src/bot_perception.py`)
- **Primary Responsibility**: Computer vision and game state recognition
- **Key Functions**:
  - `get_color()`: Extract dominant colors from unit images
  - `match_unit()`: Color-based unit identification (MSE ≤ 2000)
  - ML-based rank detection using pre-trained logistic regression
- **Performance**: Optimized to 0.082s per analysis cycle

### GUI Controller (`Src/gui.py`)
- **Primary Responsibility**: User interface and bot control
- **Threading Model**: Bot runs in separate thread to prevent UI blocking
- **Key Features**:
  - Real-time combat information display
  - Configuration management
  - Log display integration

### Handler System (`Src/bot_handler.py`)
- **Primary Responsibility**: External dependency management and utilities
- **Key Functions**:
  - `select_units()`: Unit image management
  - Automatic scrcpy binary download
  - Device health checks

## Data Flow Architecture

```
Screenshot Capture → Image Processing → Unit Recognition → Decision Making → Action Execution
       ↓                    ↓               ↓              ↓              ↓
   (scrcpy)           (OpenCV)      (Color/ML Match)   (Bot Logic)    (ADB Input)
       ↓                    ↓               ↓              ↓              ↓
  bot_feed_*.png     Color Analysis    Unit Identification  Strategy    Click/Drag
```

### Image Recognition Pipeline

1. **Screen Capture**: 
   - Uses scrcpy for low-latency capture
   - Cached as `bot_feed_{device_id}.png`
   - Resolution-dependent (requires 1600x900)

2. **Color Analysis**:
   - HSV color space conversion
   - Dominant color extraction (top 5 colors)
   - 20-pixel quantization for noise reduction

3. **Unit Matching**:
   - MSE comparison against reference colors
   - Threshold: 2000 (tuned for Dryad edge cases)
   - Fallback to 'empty.png' if no match

4. **Rank Detection**:
   - Pre-trained scikit-learn LogisticRegression
   - Model stored as `rank_model.pkl`
   - Feature extraction from unit image regions

## Threading & Concurrency

### GUI Threading Model
```python
# Main thread: GUI event loop
# Worker thread: Bot execution
threading.Thread(target=bot_execution, daemon=True)
```

### Performance Optimizations
- **Screen caching**: Reduce ADB calls
- **Color pre-computation**: Reference colors stored
- **Single-threaded vision**: Avoid OpenCV threading overhead
- **Lazy loading**: Import modules on demand

## Configuration System

### File Structure
- `config.ini`: Bot behavior settings
- `units/`: Active unit deck (copied from `all_units/`)
- `rank_model.pkl`: ML model for rank recognition
- `icons/`: UI state detection images

### Unit Selection Workflow
```python
# 1. Copy from master collection
select_units(['chemist', 'harlequin', 'bombardier', 'dryad', 'demon_hunter'])

# 2. Generate color references
for unit in units:
    colors = get_color(f'units/{unit}.png')
    
# 3. Runtime recognition
match_unit(screenshot_crop, reference_colors, unit_names)
```

## Device Communication

### ADB Integration
- **Connection**: Direct ADB via subprocess
- **Discovery**: Port scanning (typically emulator-5554)
- **Input**: Coordinate-based touch events
- **Monitoring**: Process health checks

### Scrcpy Integration
- **Purpose**: Low-latency screen mirroring
- **Mode**: Headless (no video display)
- **Client**: Python scrcpy-client wrapper
- **Fallback**: Auto-download if binary missing

## Error Handling Strategy

### Graceful Degradation
1. **Device disconnection**: Attempt reconnection
2. **Recognition failure**: Fallback to default actions
3. **Dependency missing**: Auto-download (scrcpy)
4. **Multiple devices**: Interactive selection

### Warning Suppression
```python
# Known harmless warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
```

## Development vs Production Modes

### Development (Jupyter Notebook)
- **Use case**: Experimentation and debugging
- **Features**: Interactive cell execution, variable inspection
- **Performance**: Slower due to notebook overhead
- **Path**: `sys.path.append('./Src')`

### Production (GUI/Batch)
- **Use case**: 24/7 automated operation
- **Features**: Background execution, logging
- **Performance**: Optimized for efficiency
- **Management**: Batch file launchers

## Quality Assurance System

### Testing Framework
- **Unit Tests**: Comprehensive test coverage for all core components
- **Integration Tests**: End-to-end functionality validation
- **Performance Tests**: Bottleneck identification and optimization
- **Mock Testing**: Device-independent testing capabilities

### Code Quality Tools
```python
# Automated code formatting
black --line-length=100 .
isort --profile=black .

# Static analysis
mypy Src/ --ignore-missing-imports
pylint Src/

# Security scanning
bandit -r Src/
```

### Performance Monitoring
```python
from performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
# Operations are automatically timed with decorators
# @time_function('operation_name')

# Generate performance report
print(monitor.get_performance_report())
```

### Error Recovery System
```python
from error_recovery import get_error_recovery_system

recovery = get_error_recovery_system()
# Automatic error handling with decorators
# @with_error_recovery('component_name')

# Custom recovery strategies
recovery.register_recovery_strategy('custom_error', custom_handler)
```

### Configuration Validation
```python
from config_validator import validate_bot_config

result = validate_bot_config()
if not result.is_valid:
    print("Configuration errors:", result.errors)
```

## CI/CD Pipeline

### Automated Testing
- **GitHub Actions**: Automated testing on push/PR
- **Pre-commit hooks**: Code quality checks before commits
- **Coverage reporting**: Test coverage tracking
- **Security scanning**: Dependency vulnerability checks

### Release Process
- **Automated builds**: Portable packages generated automatically
- **Version management**: Semantic versioning with changelog
- **Quality gates**: All tests must pass before release
- **Documentation**: Auto-generated from code comments

## Extensibility Points

### Adding New Units
1. Add image to `all_units/`
2. Include in `select_units()` call
3. Update `config.ini` if needed
4. Test recognition accuracy

### New Game Modes
1. Extend `bot_core.py` with new screen detection
2. Add corresponding icons to `icons/`
3. Update state machine logic
4. Test thoroughly with new UI states

### Performance Tuning
1. Adjust MSE threshold for recognition
2. Optimize color quantization parameters
3. Cache frequently accessed data
4. Profile bottlenecks with timing decorators

### Custom Recovery Strategies
```python
def custom_recovery_handler(error_context):
    # Implement custom recovery logic
    return True  # Return True if recovery successful

recovery_system = get_error_recovery_system()
recovery_system.register_recovery_strategy('my_error_pattern', custom_recovery_handler)
```
