"""
Quick version display script for Rush Royale Bot
Run this to see current version information
"""

import sys
import platform
from pathlib import Path

# Import version info from tools directory
try:
    from version import get_version_info
    version_info = get_version_info()
    
    print("=" * 60)
    print(f"🎮 {version_info['name']}")
    print(f"📦 Version: {version_info['version']}")
    print(f"🐍 Python: {version_info['python_version']}")
    print(f"💻 Platform: {platform.system()} {platform.release()}")
    print(f"📅 Released: {version_info['release_date']}")
    print(f"🏷️  Tag: {version_info['tag']}")
    print("=" * 60)
    print()
    
    # Quick feature highlights
    print("✨ Key Features in v2.0.0:")
    print("  • Python 3.13.5 with 15-20% performance boost")
    print("  • All dependencies updated to latest versions")
    print("  • Enhanced error handling and warnings suppression")
    print("  • Comprehensive documentation and changelog")
    print("  • Robust dependency conflict resolution")
    print()
    
    # Quick start guide
    print("🚀 Quick Start:")
    print("  1. Run: install.bat (first time setup)")
    print("  2. Launch: launch_gui.bat (start bot)")
    print("  3. Test: python tools\\test_dependencies.py (verify)")
    print()
    
except ImportError as e:
    print(f"❌ Could not import version info: {e}")
    print("🔧 Make sure you're in the Rush Royale Bot directory")
    print("📁 Current directory:", Path.cwd())
