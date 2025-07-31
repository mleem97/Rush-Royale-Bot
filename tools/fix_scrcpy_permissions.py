"""
Scrcpy Permission Fix Tool
Fixes common permission issues with scrcpy extraction
"""

import os
import shutil
import subprocess
import psutil
import time

def check_admin_rights():
    """Check if running with administrator privileges"""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def kill_scrcpy_processes():
    """Kill any running scrcpy processes"""
    print("🔍 Checking for running scrcpy processes...")
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'scrcpy' in proc.info['name'].lower():
                print(f"   Found scrcpy process: {proc.info['name']} (PID: {proc.info['pid']})")
                proc.kill()
                killed_processes.append(proc.info['name'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes:
        print(f"✅ Killed processes: {', '.join(killed_processes)}")
        time.sleep(2)  # Wait for processes to fully terminate
    else:
        print("✅ No scrcpy processes found")

def remove_scrcpy_folder():
    """Remove the .scrcpy folder if it exists"""
    scrcpy_path = '.scrcpy'
    
    if os.path.exists(scrcpy_path):
        print(f"🗑️  Removing {scrcpy_path} folder...")
        try:
            # Remove read-only attributes first
            for root, dirs, files in os.walk(scrcpy_path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        os.chmod(filepath, 0o777)
                    except:
                        pass
            
            shutil.rmtree(scrcpy_path)
            print("✅ Scrcpy folder removed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to remove scrcpy folder: {e}")
            return False
    else:
        print("✅ No scrcpy folder found")
        return True

def check_disk_space():
    """Check if there's enough disk space"""
    statvfs = os.statvfs('.')
    free_bytes = statvfs.f_frsize * statvfs.f_available
    free_mb = free_bytes / (1024 * 1024)
    
    print(f"💾 Available disk space: {free_mb:.1f} MB")
    
    if free_mb < 100:  # scrcpy needs ~50MB
        print("⚠️  Warning: Low disk space!")
        return False
    else:
        print("✅ Sufficient disk space available")
        return True

def fix_permissions():
    """Fix file permissions in current directory"""
    print("🔧 Checking directory permissions...")
    
    try:
        # Test write access
        test_file = 'permission_test.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("✅ Write permissions OK")
        return True
    except Exception as e:
        print(f"❌ Permission issue: {e}")
        return False

def restart_as_admin():
    """Restart the script as administrator (Windows)"""
    if os.name == 'nt':  # Windows
        import ctypes
        try:
            print("🔑 Attempting to restart as administrator...")
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", 
                "python", 
                f'"{__file__}"', 
                None, 1
            )
            return True
        except Exception as e:
            print(f"❌ Failed to restart as admin: {e}")
            return False
    return False

def main():
    """Main fix routine"""
    print("🛠️  Scrcpy Permission Fix Tool")
    print("=" * 40)
    
    # Check admin rights
    if check_admin_rights():
        print("✅ Running with administrator privileges")
    else:
        print("⚠️  Not running as administrator")
        if os.name == 'nt':
            answer = input("Would you like to restart as administrator? (y/n): ")
            if answer.lower().startswith('y'):
                if restart_as_admin():
                    return
    
    # Step 1: Kill processes
    kill_scrcpy_processes()
    
    # Step 2: Check disk space
    if not check_disk_space():
        print("❌ Insufficient disk space. Please free up some space.")
        return
    
    # Step 3: Check permissions
    if not fix_permissions():
        print("❌ Directory permission issues detected")
        if not check_admin_rights():
            print("   Try running as administrator")
        return
    
    # Step 4: Remove old scrcpy folder
    if not remove_scrcpy_folder():
        print("❌ Could not remove scrcpy folder")
        if not check_admin_rights():
            print("   Try running as administrator")
        return
    
    print("\n🎉 Permission fix completed!")
    print("\nNext steps:")
    print("1. Try starting the bot again")
    print("2. The scrcpy files will be re-downloaded automatically")
    print("3. If issues persist, run this tool as administrator")
    
    # Offer to start the bot
    answer = input("\nWould you like to start the modern GUI now? (y/n): ")
    if answer.lower().startswith('y'):
        try:
            subprocess.run(['python', 'Src\\gui_modern.py'])
        except Exception as e:
            print(f"Failed to start GUI: {e}")
            print("You can start it manually with: python Src\\gui_modern.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Fix cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    input("\nPress Enter to exit...")
