"""
System Check Utility for Rush Royale Bot
Checks all system requirements before startup
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Checks Python Version"""
    print("=== Python Version Check ===")
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ ERROR: Python 3.11+ required!")
        return False
    
    print("✅ Python Version OK")
    return True

def check_dependencies():
    """Checks installed dependencies"""
    print("\n=== Dependency Check ===")
    
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy', 
        'pandas': 'pandas',
        'sklearn': 'scikit-learn',
        'PIL': 'Pillow',
        'ppadb': 'pure-python-adb'
    }
    
    all_ok = True
    for module, package in required_packages.items():
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                print(f"❌ {package} not found")
                all_ok = False
            else:
                # Try import to get version
                try:
                    imported = importlib.import_module(module)
                    version = getattr(imported, '__version__', 'unknown')
                    print(f"✅ {package}: {version}")
                except Exception as e:
                    print(f"⚠️  {package}: installed but import error: {e}")
                    all_ok = False
        except Exception as e:
            print(f"❌ {package}: Error during check: {e}")
            all_ok = False
    
    return all_ok

def check_adb_connection():
    """Checks ADB connection to BlueStacks"""
    print("\n=== ADB Connection Check ===")
    
    try:
        # Check if ADB is available
        result = subprocess.run(['adb', 'version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ ADB available")
        else:
            print("❌ ADB not available")
            return False
            
        # Check connected devices
        result = subprocess.run(['adb', 'devices'], 
                               capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')[1:]  # Skip header
            active_devices = [d for d in devices if d.strip() and 'device' in d]
            
            if active_devices:
                print(f"✅ Found devices: {len(active_devices)}")
                for device in active_devices:
                    print(f"   - {device}")
                return True
            else:
                print("⚠️  No devices connected")
                print("   Make sure BlueStacks is running and ADB is enabled")
                return False
        else:
            print(f"❌ ADB devices error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ ADB Timeout - BlueStacks possibly not started")
        return False
    except FileNotFoundError:
        print("❌ ADB not found in PATH")
        print("   Install ADB or start BlueStacks")
        return False
    except Exception as e:
        print(f"❌ ADB error: {e}")
        return False

def check_file_structure():
    """Checks required files and directories"""
    print("\n=== File Structure Check ===")
    
    required_files = [
        'Src/gui.py',
        'Src/bot_core.py', 
        'Src/bot_handler.py',
        'Src/bot_perception.py'
    ]
    
    required_dirs = [
        'icons',
        'all_units'
    ]
    
    all_ok = True
    
    # Check files
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} missing")
            all_ok = False
    
    # Check directories
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            file_count = len(os.listdir(dir_path))
            print(f"✅ {dir_path}/ ({file_count} files)")
        else:
            print(f"❌ {dir_path}/ missing")
            all_ok = False
    
    # Create missing directories
    optional_dirs = ['units', 'OCR_inputs']
    for dir_path in optional_dirs:
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
            print(f"✅ {dir_path}/ created")
    
    return all_ok

def check_config():
    """Checks configuration file"""
    print("\n=== Configuration Check ===")
    
    if os.path.exists('config.ini'):
        print("✅ config.ini found")
        
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            required_sections = ['bot']
            for section in required_sections:
                if config.has_section(section):
                    print(f"   ✅ Section [{section}] OK")
                else:
                    print(f"   ❌ Section [{section}] missing")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading config.ini: {e}")
            return False
    else:
        print("⚠️  config.ini not found - will be created on first start")
        return True

def main():
    """Main function for System Check"""
    print("Rush Royale Bot - System Check")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies), 
        ("File Structure", check_file_structure),
        ("Configuration", check_config),
        ("ADB Connection", check_adb_connection)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name}: Unexpected error: {e}")
            results[name] = False
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ OK" if passed else "❌ ERROR"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks successful! Bot can be started.")
    else:
        print("⚠️  Some checks failed. Fix the problems before starting.")
    
    return all_passed

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
