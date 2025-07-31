#!/usr/bin/env python3
"""
Rush Royale Bot - Interface Package
User interfaces for the bot (GUI, CLI, Jupyter)
"""

# Import interface components
from .gui import ModernBotGUI
from .cli import BotCLI

# Package version
__version__ = "2.0.0"

# Available interfaces
__all__ = [
    'ModernBotGUI',
    'BotCLI'
]

# Interface information
INTERFACES_INFO = {
    'gui': {
        'description': 'Modern graphical interface using CustomTkinter',
        'main_class': 'ModernBotGUI',
        'dependencies': ['customtkinter', 'pillow'],
        'entry_point': 'interface.gui:main'
    },
    'cli': {
        'description': 'Command line interface for bot operations',
        'main_class': 'BotCLI', 
        'dependencies': [],
        'entry_point': 'interface.cli:main'
    }
}


def get_interface_info() -> dict:
    """Get information about available interfaces"""
    return INTERFACES_INFO.copy()


def check_gui_dependencies() -> bool:
    """Check if GUI dependencies are available"""
    try:
        import customtkinter
        import PIL
        return True
    except ImportError:
        return False


def launch_gui():
    """Launch the graphical interface"""
    try:
        from .gui import main
        main()
    except ImportError as e:
        print(f"GUI dependencies missing: {e}")
        print("Install with: pip install customtkinter pillow")
        return False
    except Exception as e:
        print(f"GUI launch error: {e}")
        return False


def launch_cli(args=None):
    """Launch the command line interface"""
    try:
        from .cli import main
        if args:
            import sys
            sys.argv = ['cli'] + args
        main()
    except Exception as e:
        print(f"CLI launch error: {e}")
        return False


# Auto-detect best interface
def launch_auto():
    """Launch the best available interface"""
    if check_gui_dependencies():
        print("Launching GUI interface...")
        return launch_gui()
    else:
        print("GUI not available, launching CLI interface...")
        return launch_cli(['help'])
