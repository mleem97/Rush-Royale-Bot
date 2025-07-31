#!/usr/bin/env python3
"""
Rush Royale Bot - Device Management Module
Handles ADB communication, device discovery, and screen capture
"""

import os
import time
import subprocess
from subprocess import Popen, DEVNULL
from typing import Optional, List
import logging


class DeviceManager:
    """Manages Android device connections and ADB operations"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.logger = logging.getLogger(__name__)
        self.adb_path = ".scrcpy\\adb"
        
    def get_device(self) -> Optional[str]:
        """Get available device ID, auto-discover if not specified"""
        if self.device_id:
            return self.device_id
        
        # Auto-discover devices
        devices = self.list_devices()
        
        if not devices:
            self.logger.error("No Android devices found")
            return None
        
        if len(devices) == 1:
            self.device_id = devices[0]
            self.logger.info(f"Auto-detected device: {self.device_id}")
            return self.device_id
        
        # Multiple devices - use default emulator port
        emulator_device = "emulator-5554"
        if emulator_device in devices:
            self.device_id = emulator_device
            self.logger.info(f"Using default emulator: {self.device_id}")
            return self.device_id
        
        # Use first available device
        self.device_id = devices[0]
        self.logger.warning(f"Multiple devices found, using: {self.device_id}")
        return self.device_id
    
    def list_devices(self) -> List[str]:
        """List all connected Android devices"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            devices = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            return devices
            
        except Exception as e:
            self.logger.error(f"Failed to list devices: {e}")
            return []
    
    def connect(self, device_id: str) -> bool:
        """Connect to specific device"""
        try:
            cmd = [self.adb_path, 'connect', device_id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.info(f"Connected to device: {device_id}")
                return True
            else:
                self.logger.error(f"Failed to connect to {device_id}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def shell_command(self, cmd: str) -> bool:
        """Execute ADB shell command"""
        try:
            full_cmd = [self.adb_path, '-s', self.device_id, 'shell', cmd]
            process = Popen(full_cmd, stdout=DEVNULL, stderr=DEVNULL)
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Shell command failed: {e}")
            return False
    
    def launch_game(self) -> bool:
        """Launch Rush Royale game"""
        return self.shell_command('monkey -p com.my.defense 1')
    
    def capture_screen(self, filename: str) -> bool:
        """Capture device screen to file"""
        try:
            # Use ADB screencap
            temp_file = f"/sdcard/{filename}"
            
            # Capture screen on device
            if not self.shell_command(f'screencap -p {temp_file}'):
                return False
            
            # Pull file to local system
            pull_cmd = [self.adb_path, '-s', self.device_id, 'pull', temp_file, filename]
            result = subprocess.run(pull_cmd, capture_output=True, timeout=30)
            
            # Clean up temp file on device
            self.shell_command(f'rm {temp_file}')
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return False
    
    def install_app(self, apk_path: str) -> bool:
        """Install APK on device"""
        try:
            cmd = [self.adb_path, '-s', self.device_id, 'install', apk_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"App installation failed: {e}")
            return False
    
    def restart_adb(self) -> bool:
        """Restart ADB server"""
        try:
            # Kill ADB server
            subprocess.run([self.adb_path, 'kill-server'], capture_output=True, timeout=10)
            time.sleep(2)
            
            # Start ADB server
            result = subprocess.run([self.adb_path, 'start-server'], capture_output=True, timeout=10)
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"ADB restart failed: {e}")
            return False
    
    def get_device_info(self) -> dict:
        """Get device information"""
        info = {}
        
        try:
            # Get device model
            result = subprocess.run(
                [self.adb_path, '-s', self.device_id, 'shell', 'getprop', 'ro.product.model'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info['model'] = result.stdout.strip()
            
            # Get Android version
            result = subprocess.run(
                [self.adb_path, '-s', self.device_id, 'shell', 'getprop', 'ro.build.version.release'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info['android_version'] = result.stdout.strip()
            
            # Get screen resolution
            result = subprocess.run(
                [self.adb_path, '-s', self.device_id, 'shell', 'wm', 'size'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                size_line = result.stdout.strip()
                if 'Physical size:' in size_line:
                    resolution = size_line.split('Physical size:')[1].strip()
                    info['resolution'] = resolution
            
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
        
        return info
    
    def is_device_connected(self) -> bool:
        """Check if device is connected and responsive"""
        if not self.device_id:
            return False
        
        try:
            # Simple test command
            result = subprocess.run(
                [self.adb_path, '-s', self.device_id, 'shell', 'echo', 'test'],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and 'test' in result.stdout
            
        except Exception:
            return False


# Utility functions for device discovery
def scan_for_devices() -> List[str]:
    """Scan for available Android devices"""
    manager = DeviceManager()
    return manager.list_devices()


def get_default_device() -> Optional[str]:
    """Get default device (emulator-5554 or first available)"""
    devices = scan_for_devices()
    
    if not devices:
        return None
    
    # Prefer emulator
    if "emulator-5554" in devices:
        return "emulator-5554"
    
    return devices[0]
