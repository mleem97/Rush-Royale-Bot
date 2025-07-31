"""
Rush Royale Bot - System Health Check
Comprehensive system verification before bot startup
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path

class HealthChecker:
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.warnings = []
        self.errors = []
    
    def run_check(self, name, check_function):
        """Run a single health check"""
        self.checks_total += 1
        print(f"🔍 {name}...", end=" ")
        
        try:
            result = check_function()
            if result is True:
                print("✅ OK")
                self.checks_passed += 1
                return True
            elif isinstance(result, str):
                print(f"⚠️  {result}")
                self.warnings.append(f"{name}: {result}")
                return False
            else:
                print("❌ FAILED")
                self.errors.append(f"{name}: Check failed")
                return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.errors.append(f"{name}: {str(e)}")
            return False
    
    def check_python_version(self):
        """Check Python version"""
        version = sys.version_info
        if version.major == 3 and version.minor == 13:
            return True
        else:
            return f"Expected Python 3.13, got {version.major}.{version.minor}"
    
    def check_critical_imports(self):
        """Check critical Python packages"""
        critical_packages = [
            'numpy', 'pandas', 'cv2', 'scrcpy', 'sklearn', 
            'PIL', 'matplotlib', 'adbutils', 'tkinter'
        ]
        
        missing = []
        for package in critical_packages:
            try:
                if package == 'cv2':
                    importlib.import_module('cv2')
                elif package == 'PIL':
                    importlib.import_module('PIL.Image')
                elif package == 'sklearn':
                    importlib.import_module('sklearn.ensemble')
                else:
                    importlib.import_module(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            return f"Missing packages: {', '.join(missing)}"
        return True
    
    def check_bot_files(self):
        """Check bot source files"""
        required_files = [
            'Src/gui.py',
            'Src/bot_core.py', 
            'Src/bot_handler.py',
            'Src/bot_perception.py',
            'Src/port_scan.py',
            'rank_model.pkl',
            'requirements.txt'
        ]
        
        missing = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing.append(file_path)
        
        if missing:
            return f"Missing files: {', '.join(missing)}"
        return True
    
    def check_adb_connection(self):
        """Check ADB server and device connectivity"""
        try:
            # Check ADB server with shorter timeout
            result = subprocess.run('.scrcpy\\adb version', shell=True, 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode != 0:
                return "ADB not accessible"
            
            # Check devices with shorter timeout
            result = subprocess.run('.scrcpy\\adb devices', shell=True,
                                  capture_output=True, text=True, timeout=3)
            if result.returncode != 0:
                return "ADB devices command failed"
            
            # Quick device count check
            device_lines = [line for line in result.stdout.strip().split('\n')[1:] 
                          if line.strip() and 'device' in line.lower()]
            
            if not device_lines:
                return "No devices found"
            elif len(device_lines) > 1:
                return f"Multiple devices detected ({len(device_lines)} devices)"
            else:
                return True
                
        except subprocess.TimeoutExpired:
            return "ADB timeout"
        except Exception as e:
            return f"ADB check failed: {str(e)}"
    
    def check_bluestacks_process(self):
        """Check if Bluestacks is running"""
        try:
            result = subprocess.run('tasklist | findstr -i bluestacks', shell=True,
                                  capture_output=True, text=True, timeout=3)
            if result.stdout.strip():
                return True
            else:
                return "Bluestacks not running"
        except Exception:
            return "Could not check Bluestacks status"
    
    def check_disk_space(self):
        """Check available disk space"""
        try:
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_mb = free_bytes / (1024 * 1024)
            
            if free_mb < 100:  # Less than 100MB
                return f"Low disk space: {free_mb:.0f}MB free"
            return True
        except Exception:
            return "Could not check disk space"
    
    def check_config_files(self):
        """Check configuration and model files"""
        issues = []
        
        # Check if config.ini exists
        if not Path('config.ini').exists():
            issues.append("config.ini missing (will be created)")
        
        # Check ML model
        if not Path('rank_model.pkl').exists():
            issues.append("rank_model.pkl missing")
        
        # Check important directories
        required_dirs = ['Src', 'all_units', 'icons', '.scrcpy']
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                issues.append(f"{dir_name}/ directory missing")
        
        if issues:
            return "; ".join(issues)
        return True
    
    def run_all_checks(self):
        """Run all health checks"""
        print("🏥 Rush Royale Bot - System Health Check")
        print("=" * 50)
        
        # Core system checks
        self.run_check("Python Version", self.check_python_version)
        self.run_check("Critical Imports", self.check_critical_imports)
        self.run_check("Bot Files", self.check_bot_files)
        self.run_check("Configuration", self.check_config_files)
        
        # System checks
        self.run_check("Disk Space", self.check_disk_space)
        self.run_check("Bluestacks Process", self.check_bluestacks_process)
        self.run_check("ADB Connection", self.check_adb_connection)
        
        # Summary
        print("\n" + "=" * 50)
        print(f"📊 Health Check Results: {self.checks_passed}/{self.checks_total} passed")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        print("\n" + "=" * 50)
        
        if self.errors:
            print("❌ HEALTH CHECK FAILED - Critical issues found")
            print("💡 Please fix the errors above before starting the bot")
            return False
        elif self.warnings:
            print("⚠️  HEALTH CHECK PASSED WITH WARNINGS")
            print("💡 Bot should work, but issues may occur")
            return True
        else:
            print("✅ HEALTH CHECK PASSED - All systems operational")
            print("🚀 Bot is ready to run!")
            return True

def main():
    """Main function"""
    checker = HealthChecker()
    result = checker.run_all_checks()
    
    # Return appropriate exit code
    if not result and checker.errors:
        sys.exit(1)  # Critical errors
    elif checker.warnings:
        sys.exit(2)  # Warnings present
    else:
        sys.exit(0)  # All good

if __name__ == "__main__":
    main()
