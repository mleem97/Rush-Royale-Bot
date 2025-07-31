#!/usr/bin/env python3
"""
Rush Royale Bot - Modules Package
Consolidated bot functionality modules
"""

# Import all major module components
from .combat import CombatStrategy
from .debug import DebugSystem, get_debug_system, enable_debug, disable_debug, debug_timing
from .navigation import NavigationSystem, GameState
from .recognition import UnitRecognizer
from .automation import AutomationEngine, AutomationTask, BattleSession

# Module version
__version__ = "2.0.0"

# Available modules
__all__ = [
    # Combat module
    'CombatStrategy',
    
    # Debug module
    'DebugSystem',
    'get_debug_system',
    'enable_debug',
    'disable_debug',
    'debug_timing',
    
    # Navigation module
    'NavigationSystem',
    'GameState',
    
    # Recognition module
    'UnitRecognizer',
    
    # Automation module
    'AutomationEngine',
    'AutomationTask',
    'BattleSession'
]

# Module information
MODULES_INFO = {
    'combat': {
        'description': 'Combat strategy and unit merging logic',
        'main_class': 'CombatStrategy',
        'dependencies': ['pandas', 'numpy']
    },
    'debug': {
        'description': 'Comprehensive debugging and monitoring system',
        'main_class': 'DebugSystem',
        'dependencies': ['opencv-python', 'numpy']
    },
    'navigation': {
        'description': 'Game navigation and state detection',
        'main_class': 'NavigationSystem',
        'dependencies': ['opencv-python', 'numpy']
    },
    'recognition': {
        'description': 'Advanced unit recognition and game state analysis',
        'main_class': 'UnitRecognizer',
        'dependencies': ['opencv-python', 'numpy', 'pandas', 'scikit-learn']
    },
    'automation': {
        'description': 'High-level automation workflows and battle management',
        'main_class': 'AutomationEngine',
        'dependencies': ['pandas']
    }
}


def get_module_info() -> dict:
    """Get information about all available modules"""
    return MODULES_INFO.copy()


def check_dependencies():
    """Check if all required dependencies are available"""
    import importlib
    
    missing_deps = []
    all_deps = set()
    
    # Collect all dependencies
    for module_info in MODULES_INFO.values():
        all_deps.update(module_info['dependencies'])
    
    # Check each dependency
    for dep in all_deps:
        try:
            importlib.import_module(dep.replace('-', '_'))
        except ImportError:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"Missing dependencies: {', '.join(missing_deps)}")
        print("Please install them using: pip install " + " ".join(missing_deps))
        return False
    else:
        print("All module dependencies are satisfied")
        return True


# Initialize module (check dependencies on import)
if __name__ != "__main__":
    import warnings
    try:
        # Suppress warnings during dependency check
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            check_dependencies()
    except Exception:
        pass  # Ignore any errors during initialization
