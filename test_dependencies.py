#!/usr/bin/env python
"""
Rush Royale Bot - Dependency Validation Script
Python 3.13 Compatible

This script validates that all required dependencies are installed
and compatible with the current Python version.

Usage:
    python test_dependencies.py
    
Exit codes:
    0 - All dependencies satisfied
    1 - Missing or incompatible dependencies
"""
from __future__ import annotations

import sys
import importlib.metadata
from typing import NamedTuple
from packaging import version


class Dependency(NamedTuple):
    """Represents a package dependency with version constraints."""
    name: str
    import_name: str
    min_version: str | None = None
    max_version: str | None = None
    optional: bool = False


# Core dependencies required for the bot
REQUIRED_DEPENDENCIES: list[Dependency] = [
    # Core Data & ML
    Dependency("numpy", "numpy", "2.0.0", "3.0.0"),
    Dependency("pandas", "pandas", "2.0.0", "3.0.0"),
    Dependency("scikit-learn", "sklearn", "1.4.0", "2.0.0"),
    
    # Computer Vision & Image Processing
    Dependency("opencv-python", "cv2", "4.8.0", "5.0.0"),
    Dependency("Pillow", "PIL", "10.0.0", "13.0.0"),
    
    # GUI & Visualization
    Dependency("matplotlib", "matplotlib", "3.8.0", "4.0.0"),
    Dependency("customtkinter", "customtkinter", "5.2.0", "6.0.0"),
    
    # Jupyter/Development
    Dependency("ipykernel", "ipykernel", "6.25.0", "7.0.0", optional=True),
    Dependency("ipywidgets", "ipywidgets", "8.1.0", "9.0.0", optional=True),
    
    # System & Utilities
    Dependency("psutil", "psutil", "5.9.0", "8.0.0"),
    Dependency("tqdm", "tqdm", "4.65.0", "5.0.0"),
    
    # Android ADB Control (dev versions allowed)
    Dependency("pure-python-adb", "ppadb", "0.3.0.dev0", None),
    
    # HTTP Requests
    Dependency("requests", "requests", "2.31.0", "3.0.0"),
    
    # Configuration
    Dependency("configparser", "configparser", "5.3.0", "6.0.0"),
]


def check_python_version() -> bool:
    """Verify Python version is 3.13+."""
    minimum = (3, 13)
    current = sys.version_info[:2]
    
    if current < minimum:
        print(f"❌ Python {minimum[0]}.{minimum[1]}+ required, found {current[0]}.{current[1]}")
        print(f"   Download Python 3.13: https://www.python.org/downloads/")
        return False
    
    print(f"✅ Python {current[0]}.{current[1]} - OK")
    return True


def check_dependency(dep: Dependency) -> bool:
    """Check if a single dependency is installed and meets version constraints."""
    try:
        # Try to import the module
        module = __import__(dep.import_name)
        
        # Get installed version
        try:
            installed_version = importlib.metadata.version(dep.name)
        except importlib.metadata.PackageNotFoundError:
            # Fallback: try to get version from module
            installed_version = getattr(module, "__version__", "unknown")
        
        # Check version constraints
        if installed_version == "unknown":
            print(f"⚠️  {dep.name} installed (version unknown)")
            return True
            
        v = version.parse(installed_version)
        
        if dep.min_version and v < version.parse(dep.min_version):
            print(f"❌ {dep.name} {installed_version} < {dep.min_version} (minimum)")
            return False
            
        if dep.max_version and v >= version.parse(dep.max_version):
            print(f"❌ {dep.name} {installed_version} >= {dep.max_version} (maximum)")
            return False
        
        print(f"✅ {dep.name} {installed_version} - OK")
        return True
        
    except ImportError as e:
        if dep.optional:
            print(f"⚠️  {dep.name} not installed (optional)")
            return True
        else:
            print(f"❌ {dep.name} not installed: {e}")
            return False
    except Exception as e:
        print(f"⚠️  {dep.name} check failed: {e}")
        return dep.optional


def check_adb_availability() -> bool:
    """Check if ADB is available in the system."""
    import shutil
    import os
    from pathlib import Path
    
    # Check common locations
    adb_locations = [
        shutil.which("adb"),
        shutil.which("adb.exe"),
        os.getenv("ADB_PATH"),
    ]
    
    # Add common installation paths
    common_paths = [
        Path("C:/Program Files/scrcpy/adb.exe"),
        Path(".scrcpy/adb.exe"),
        Path("scrcpy/adb.exe"),
    ]
    
    for path in common_paths:
        if path.exists():
            adb_locations.append(str(path))
    
    adb_found = any(loc for loc in adb_locations if loc)
    
    if adb_found:
        print(f"✅ ADB found - OK")
    else:
        print(f"⚠️  ADB not found in PATH (may still work with pure-python-adb)")
    
    return True  # Not critical, pure-python-adb can work without system ADB


def main() -> int:
    """Run all dependency checks."""
    print("=" * 60)
    print("Rush Royale Bot - Dependency Validation")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Check Python version
    print("📦 Python Version:")
    if not check_python_version():
        all_ok = False
    print()
    
    # Check all dependencies
    print("📦 Required Dependencies:")
    for dep in REQUIRED_DEPENDENCIES:
        if not check_dependency(dep):
            all_ok = False
    print()
    
    # Check ADB
    print("📦 System Tools:")
    check_adb_availability()
    print()
    
    # Summary
    print("=" * 60)
    if all_ok:
        print("✅ All dependencies satisfied!")
        return 0
    else:
        print("❌ Some dependencies are missing or incompatible.")
        print("   Run: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
