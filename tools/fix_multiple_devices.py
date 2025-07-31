"""
Quick fix for "more than one device/emulator" error
This script will help you select a single device for the bot to use
"""

import subprocess
import os
import sys

def run_adb_command(command, capture_output=True):
    """Run ADB command"""
    try:
        if capture_output:
            result = subprocess.run(f'.scrcpy\\adb {command}', shell=True, 
                                  capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        else:
            result = subprocess.run(f'.scrcpy\\adb {command}', shell=True)
            return "", "", result.returncode
    except Exception as e:
        return "", str(e), 1

def get_connected_devices():
    """Get list of connected devices"""
    stdout, stderr, code = run_adb_command("devices")
    if code != 0:
        print(f"❌ Error getting devices: {stderr}")
        return []
    
    devices = []
    lines = stdout.strip().split('\n')[1:]  # Skip header
    for line in lines:
        if line.strip() and '\t' in line:
            device_id = line.split('\t')[0]
            status = line.split('\t')[1]
            if status == "device":
                devices.append(device_id)
    
    return devices

def disconnect_all_except(keep_device):
    """Disconnect all devices except the specified one"""
    devices = get_connected_devices()
    disconnected = []
    
    for device in devices:
        if device != keep_device:
            print(f"🔌 Disconnecting: {device}")
            stdout, stderr, code = run_adb_command(f"disconnect {device}")
            if code == 0:
                disconnected.append(device)
                print(f"✅ Disconnected: {device}")
            else:
                print(f"⚠️  Could not disconnect {device}: {stderr}")
    
    return disconnected

def main():
    print("🔧 Rush Royale Bot - Device Conflict Resolver")
    print("=" * 55)
    
    # Get current devices
    devices = get_connected_devices()
    
    if len(devices) == 0:
        print("❌ No devices found")
        return
    
    if len(devices) == 1:
        print(f"✅ Only one device connected: {devices[0]}")
        print("No action needed - you can start the bot now!")
        return
    
    print(f"⚠️  Found {len(devices)} devices - this causes the 'more than one device' error")
    print("\n📱 Connected devices:")
    for i, device in enumerate(devices, 1):
        device_type = "📱 Emulator" if "emulator" in device else "🔌 Device"
        print(f"  {i}. {device_type}: {device}")
    
    print(f"\n🎯 Which device should the bot use?")
    print("   (Others will be temporarily disconnected)")
    
    while True:
        try:
            choice = input(f"\nEnter device number (1-{len(devices)}): ")
            choice = int(choice)
            
            if 1 <= choice <= len(devices):
                selected_device = devices[choice - 1]
                break
            else:
                print("❌ Invalid choice, please try again")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Cancelled")
            return
    
    print(f"\n🎯 Using device: {selected_device}")
    
    # Disconnect other devices
    disconnected = disconnect_all_except(selected_device)
    
    if disconnected:
        print(f"\n✅ Disconnected {len(disconnected)} devices")
        print("🤖 You can now start the bot - it should work without errors!")
        print("\n💡 To reconnect devices later, restart Bluestacks or run:")
        for device in disconnected:
            if "emulator" not in device:  # Don't show reconnect for emulators
                print(f"     .scrcpy\\adb connect {device}")
    else:
        print("\n✅ Ready to go!")
    
    # Test the selected device
    print(f"\n🧪 Testing connection to {selected_device}...")
    stdout, stderr, code = run_adb_command(f"-s {selected_device} shell echo 'test'")
    if code == 0:
        print("✅ Device connection test passed!")
        print("🚀 Ready to launch the bot!")
    else:
        print(f"❌ Device test failed: {stderr}")

if __name__ == "__main__":
    main()
