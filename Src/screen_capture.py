"""
Rush Royale Bot - Screen Capture Module
Python 3.13 Compatible

Handles screenshot capture using multiple methods:
- scrcpy executable (fastest, highest quality)
- pure-python-adb screencap (reliable)
- ADB shell fallback (last resort)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import logging
from pathlib import Path
from subprocess import Popen, DEVNULL
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from .adb_controller import ADBController


class ScreenCapture:
    """
    Manages screen capture from Android device.
    
    Supports multiple capture methods with automatic fallback:
    1. scrcpy executable (fastest)
    2. pure-python-adb (reliable)
    3. ADB shell command (fallback)
    """
    
    def __init__(
        self,
        adb_controller: 'ADBController',
        bot_id: str,
        logger: logging.Logger | None = None
    ):
        """
        Initialize screen capture.
        
        Args:
            adb_controller: ADB controller instance
            bot_id: Bot identifier for screenshot filenames
            logger: Optional logger instance
        """
        self.adb = adb_controller
        self.bot_id = bot_id
        self.logger = logger or logging.getLogger(__name__)
        
        # Current screen image
        self.screen_rgb: np.ndarray | None = None
        
        # scrcpy process management
        self.scrcpy_process: Popen | None = None
        self.scrcpy_executable = self._find_scrcpy_executable()
        
        # Take initial screenshot
        self.capture()
    
    @property
    def screenshot_path(self) -> str:
        """Get screenshot file path."""
        return f'bot_feed_{self.bot_id}.png'
    
    def _find_scrcpy_executable(self) -> str | None:
        """
        Find scrcpy executable in common locations.
        
        Returns:
            Path to scrcpy executable or None
        """
        possible_paths = [
            'scrcpy.exe',  # In PATH
            r'C:\Program Files\scrcpy\scrcpy.exe',
            r'C:\Program Files (x86)\scrcpy\scrcpy.exe',
            r'.\scrcpy\scrcpy.exe',
            r'.\bin\scrcpy.exe',
            r'.scrcpy\scrcpy.exe',
        ]
        
        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                self.logger.info(f'Found scrcpy at: {path}')
                return path
        
        self.logger.warning('scrcpy executable not found - will use ADB screencap fallback')
        return None
    
    def start_scrcpy_mirror(self) -> bool:
        """
        Start scrcpy process for screen mirroring.
        
        Returns:
            True if started successfully
        """
        if not self.scrcpy_executable:
            return False
        
        try:
            cmd = [
                self.scrcpy_executable,
                '--serial', self.adb.device_serial,
                '--no-control',  # View only
                '--window-title', f'RR Bot {self.adb.device_serial}',
                '--window-width', '800',
                '--window-height', '450'
            ]
            
            self.scrcpy_process = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
            self.logger.info('Started scrcpy process for screen mirroring')
            time.sleep(2)  # Give scrcpy time to start
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start scrcpy: {e}')
            self.scrcpy_process = None
            return False
    
    def stop_scrcpy_mirror(self) -> None:
        """Stop scrcpy mirroring process."""
        if self.scrcpy_process:
            try:
                self.scrcpy_process.terminate()
                self.scrcpy_process.wait(timeout=5)
                self.logger.info('Stopped scrcpy process')
            except subprocess.TimeoutExpired:
                self.scrcpy_process.kill()
                self.logger.warning('Force killed scrcpy process')
            except Exception as e:
                self.logger.error(f'Error stopping scrcpy: {e}')
            finally:
                self.scrcpy_process = None
    
    def _try_scrcpy_screenshot(self, output_path: str) -> bool:
        """
        Try taking screenshot using scrcpy/ADB exec-out.
        
        Args:
            output_path: Path to save screenshot
            
        Returns:
            True if successful
        """
        if not self.scrcpy_executable:
            return False
        
        try:
            cmd = ['adb', '-s', self.adb.device_serial, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:
            return False
    
    def _try_adb_screenshot(self, output_path: str) -> bool:
        """
        Try taking screenshot using pure-python-adb.
        
        Args:
            output_path: Path to save screenshot
            
        Returns:
            True if successful
        """
        try:
            screencap = self.adb.screencap()
            if screencap and len(screencap) > 1000:
                with open(output_path, 'wb') as f:
                    f.write(screencap)
                return True
        except Exception as e:
            self.logger.debug(f'ADB screencap failed: {e}')
        return False
    
    def _try_shell_screenshot(self, output_path: str) -> bool:
        """
        Try taking screenshot using shell ADB command.
        
        Args:
            output_path: Path to save screenshot
            
        Returns:
            True if successful
        """
        try:
            cmd = ['adb', '-s', self.adb.device_serial, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:
            return False
    
    def capture(self) -> np.ndarray | None:
        """
        Take screenshot of device screen.
        
        Returns:
            Screenshot as numpy array (BGR format) or None
        """
        output_path = self.screenshot_path
        
        # Try methods in order of preference
        if self.scrcpy_executable and self._try_scrcpy_screenshot(output_path):
            self.logger.debug('Screenshot taken via scrcpy executable')
        elif self._try_adb_screenshot(output_path):
            self.logger.debug('Screenshot taken via pure-python-adb')
        elif self._try_shell_screenshot(output_path):
            self.logger.debug('Screenshot taken via ADB shell')
        else:
            self.logger.error('All screenshot methods failed!')
            return None
        
        # Load and validate screenshot
        try:
            new_img = cv2.imread(output_path)
            if new_img is not None and new_img.shape[0] > 0 and new_img.shape[1] > 0:
                self.screen_rgb = new_img
                self.logger.debug(f'Screenshot loaded: {new_img.shape}')
                return new_img
            else:
                self.logger.warning(f'Invalid screenshot file: {output_path}')
        except Exception as e:
            self.logger.error(f'Failed to load screenshot: {e}')
        
        return None
    
    # Alias for backward compatibility
    getScreen = capture
    
    def crop(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        save_path: str = 'icon.png'
    ) -> np.ndarray | None:
        """
        Crop region from current screenshot.
        
        Args:
            x: Left edge X coordinate
            y: Top edge Y coordinate
            width: Crop width
            height: Crop height
            save_path: Path to save cropped image
            
        Returns:
            Cropped image or None
        """
        if self.screen_rgb is None:
            return None
        
        cropped = self.screen_rgb[y:y + height, x:x + width]
        cv2.imwrite(save_path, cropped)
        return cropped
    
    # Alias for backward compatibility
    crop_img = crop
    
    @property
    def current_screen(self) -> np.ndarray | None:
        """Get current screen image."""
        return self.screen_rgb
    
    @property
    def grayscale(self) -> np.ndarray | None:
        """Get current screen as grayscale."""
        if self.screen_rgb is None:
            return None
        return cv2.cvtColor(self.screen_rgb, cv2.COLOR_BGR2GRAY)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_scrcpy_mirror()
        
        # Optionally remove screenshot file
        if os.path.exists(self.screenshot_path):
            try:
                os.remove(self.screenshot_path)
            except Exception:
                pass
