"""
ADB Device Management Utility for Rush Royale Bot
Helps manage multiple Android devices/emulators
"""

import subprocess
import sys
from pathlib import Path

def run_adb_command(command):
    """Run an ADB command and return the output"""
    try:
        result = subprocess.run(f'.scrcpy\\adb {command}', shell=True, 
                              capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def list_devices():
    """List all connected ADB devices"""
    print("🔍 Scanning for ADB devices...")
    stdout, stderr, code = run_adb_command("devices -l")
    
    if code != 0:
        print(f"❌ Error running ADB: {stderr}")
        return []
    
    lines = stdout.strip().split('\n')
    devices = []
    
    print("\n📱 Connected Devices:")
    print("-" * 50)
    
    for i, line in enumerate(lines[1:], 1):  # Skip header
        if line.strip():
            # Handle both tab-separated and space-separated formats
            if '\t' in line:
                parts = line.split('\t')
                device_id = parts[0].strip()
                status = parts[1].strip() if len(parts) > 1 else "unknown"
            else:
                # Try to parse without tab (common format issue)
                parts = line.strip().split()
                if len(parts) >= 2:
                    # Look for common status words at the end
                    if parts[-1] in ['device', 'offline', 'unauthorized', 'unknown']:
                        status = parts[-1]
                        device_id = ''.join(parts[:-1])
                    else:
                        device_id = parts[0]
                        status = ' '.join(parts[1:]) if len(parts) > 1 else "unknown"
                else:
                    device_id = line.strip()
                    status = "unknown"
            
            # Extract additional info
            info = ""
            if '\t' in line and len(line.split('\t')) > 2:
                info = line.split('\t')[2]
            
            # Skip offline devices for the main list
            if status == "offline":
                continue
            
            devices.append({
                'id': device_id,
                'status': status,
                'info': info,
                'index': len(devices) + 1
            })
            
            # Determine device type
            if 'emulator' in device_id:
                device_type = "📱 Emulator"
            elif ':' in device_id:
                device_type = "🌐 Network Device"  
            else:
                device_type = "🔌 USB Device"
            
            status_emoji = "✅" if status == "device" else "⚠️"
            
            print(f"{i}. {status_emoji} {device_type}")
            print(f"   ID: {device_id}")
            print(f"   Status: {status}")
            if info:
                print(f"   Info: {info}")
            print()
    
    if not devices:
        print("❌ No devices found!")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Bluestacks is running")
        print("   2. Enable ADB in Bluestacks settings")
        print("   3. Try: python device_manager.py --restart-adb")
    
    return devices

def restart_adb():
    """Restart ADB server"""
    print("🔄 Restarting ADB server...")
    
    # Kill server
    stdout, stderr, code = run_adb_command("kill-server")
    if code == 0:
        print("✅ ADB server stopped")
    else:
        print(f"⚠️  Warning stopping ADB: {stderr}")
    
    # Start server
    stdout, stderr, code = run_adb_command("start-server")
    if code == 0:
        print("✅ ADB server started")
    else:
        print(f"❌ Error starting ADB: {stderr}")
        return False
    
    # List devices after restart
    list_devices()
    return True

def test_device(device_id):
    """Test connection to a specific device"""
    print(f"🧪 Testing device: {device_id}")
    
    # Test basic connection
    stdout, stderr, code = run_adb_command(f"-s {device_id} shell echo 'test'")
    if code != 0:
        print(f"❌ Cannot connect to device: {stderr}")
        return False
    
    print("✅ Device connection OK")
    
    # Test Rush Royale app
    stdout, stderr, code = run_adb_command(f"-s {device_id} shell pm list packages | find \"com.my.defense\"")
    if "com.my.defense" in stdout:
        print("✅ Rush Royale app found")
    else:
        print("⚠️  Rush Royale app not found")
    
    # Get device info
    stdout, _, _ = run_adb_command(f"-s {device_id} shell getprop ro.product.model")
    if stdout.strip():
        print(f"📱 Device model: {stdout.strip()}")
    
    stdout, _, _ = run_adb_command(f"-s {device_id} shell getprop ro.build.version.release")
    if stdout.strip():
        print(f"🤖 Android version: {stdout.strip()}")
    
    return True

def select_device():
    """Interactive device selection"""
    devices = list_devices()
    if not devices:
        return None
    
    if len(devices) == 1:
        print(f"✅ Using single device: {devices[0]['id']}")
        return devices[0]['id']
    
    print(f"\n🎯 Multiple devices found. Please select one:")
    print("0. Auto-select (use first emulator or device)")
    
    while True:
        try:
            choice = input("\nEnter device number (0-{}): ".format(len(devices)))
            choice = int(choice)
            
            if choice == 0:
                # Auto-select logic
                emulators = [d for d in devices if 'emulator' in d['id']]
                if emulators:
                    selected = emulators[0]['id']
                    print(f"✅ Auto-selected emulator: {selected}")
                else:
                    selected = devices[0]['id']
                    print(f"✅ Auto-selected device: {selected}")
                return selected
            
            elif 1 <= choice <= len(devices):
                selected = devices[choice-1]['id']
                print(f"✅ Selected device: {selected}")
                return selected
            else:
                print("❌ Invalid choice, please try again")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Cancelled")
            return None

def main():
    """Main function"""
    print("🤖 Rush Royale Bot - ADB Device Manager")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--list":
            list_devices()
        elif command == "--restart-adb":
            restart_adb()
        elif command == "--select":
            device = select_device()
            if device:
                test_device(device)
        elif command.startswith("--test="):
            device_id = command.split("=", 1)[1]
            test_device(device_id)
        else:
            print("❌ Unknown command")
            print_help()
    else:
        # Interactive mode
        print("\n🎯 What would you like to do?")
        print("1. List all devices")
        print("2. Restart ADB server") 
        print("3. Select and test device")
        print("4. Exit")
        
        try:
            choice = input("\nEnter choice (1-4): ")
            
            if choice == "1":
                list_devices()
            elif choice == "2":
                restart_adb()
            elif choice == "3":
                device = select_device()
                if device:
                    test_device(device)
            elif choice == "4":
                print("👋 Goodbye!")
            else:
                print("❌ Invalid choice")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")

def print_help():
    """Print help information"""
    print("\n📖 Usage:")
    print("  python device_manager.py                 # Interactive mode")
    print("  python device_manager.py --list          # List all devices")
    print("  python device_manager.py --restart-adb   # Restart ADB server")
    print("  python device_manager.py --select        # Select device interactively")
    print("  python device_manager.py --test=DEVICE   # Test specific device")

if __name__ == "__main__":
    main()
