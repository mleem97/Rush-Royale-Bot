#!/usr/bin/env python3
"""
Advanced error recovery system for Rush Royale Bot
Handles various error conditions and implements recovery strategies
"""

import time
import logging
import traceback
import subprocess
from enum import Enum
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass
import functools


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Minor issues, continue operation
    MEDIUM = "medium"    # Moderate issues, retry operation
    HIGH = "high"        # Serious issues, restart component
    CRITICAL = "critical"  # Fatal issues, stop bot


@dataclass
class ErrorContext:
    """Context information for error handling"""
    error_type: str
    error_message: str
    severity: ErrorSeverity
    component: str
    timestamp: float
    traceback_info: str
    additional_data: Dict = None


class ErrorRecoverySystem:
    """Advanced error recovery and handling system"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        self.max_retry_attempts = 3
        self.backoff_multiplier = 2.0
        self.error_history = []
        
        # Register default recovery strategies
        self._register_default_strategies()
        
        self.logger.info("Error recovery system initialized")
    
    def _register_default_strategies(self):
        """Register default error recovery strategies"""
        self.recovery_strategies.update({
            'device_connection_error': self._recover_device_connection,
            'scrcpy_connection_error': self._recover_scrcpy_connection,
            'unit_recognition_error': self._recover_unit_recognition,
            'screen_capture_error': self._recover_screen_capture,
            'file_not_found_error': self._recover_file_not_found,
            'permission_error': self._recover_permission_error,
            'memory_error': self._recover_memory_error,
            'timeout_error': self._recover_timeout_error,
        })
    
    def handle_error(self, error: Exception, component: str, **context) -> bool:
        """
        Handle an error with appropriate recovery strategy
        Returns True if error was handled and operation can continue
        """
        error_type = type(error).__name__.lower()
        error_key = f"{component}_{error_type}"
        
        # Create error context
        error_context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            severity=self._determine_severity(error, component),
            component=component,
            timestamp=time.time(),
            traceback_info=traceback.format_exc(),
            additional_data=context
        )
        
        # Record error
        self._record_error(error_key, error_context)
        
        # Log error
        self.logger.error(
            f"Error in {component}: {error_type} - {error_context.error_message}"
        )
        
        # Check if we should attempt recovery
        if not self._should_attempt_recovery(error_key, error_context):
            self.logger.critical(f"Too many errors for {error_key}, aborting recovery")
            return False
        
        # Attempt recovery
        return self._attempt_recovery(error_key, error_context)
    
    def _determine_severity(self, error: Exception, component: str) -> ErrorSeverity:
        """Determine error severity based on error type and component"""
        error_type = type(error).__name__.lower()
        
        critical_errors = ['systemexit', 'keyboardinterrupt', 'memoryerror']
        high_severity_errors = ['connectionerror', 'timeouterror', 'oserror']
        medium_severity_errors = ['filenotfounderror', 'permissionerror', 'valueerror']
        
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        elif error_type in high_severity_errors:
            return ErrorSeverity.HIGH
        elif error_type in medium_severity_errors:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _record_error(self, error_key: str, error_context: ErrorContext):
        """Record error occurrence"""
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.error_history.append(error_context)
        
        # Keep only recent error history (last 100 errors)
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
    
    def _should_attempt_recovery(self, error_key: str, error_context: ErrorContext) -> bool:
        """Determine if recovery should be attempted"""
        error_count = self.error_counts.get(error_key, 0)
        
        # Never recover from critical errors
        if error_context.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Check retry limits based on severity
        max_attempts = {
            ErrorSeverity.LOW: 5,
            ErrorSeverity.MEDIUM: 3,
            ErrorSeverity.HIGH: 2,
        }.get(error_context.severity, 1)
        
        return error_count <= max_attempts
    
    def _attempt_recovery(self, error_key: str, error_context: ErrorContext) -> bool:
        """Attempt to recover from the error"""
        # Find appropriate recovery strategy
        strategy_key = None
        for key in self.recovery_strategies:
            if key in error_key or error_context.error_type in key:
                strategy_key = key
                break
        
        if not strategy_key:
            self.logger.warning(f"No recovery strategy found for {error_key}")
            return False
        
        # Apply backoff delay
        attempt_number = self.error_counts.get(error_key, 1)
        delay = min(30, attempt_number * self.backoff_multiplier)  # Max 30 seconds
        
        self.logger.info(f"Attempting recovery for {error_key} (attempt {attempt_number})")
        time.sleep(delay)
        
        try:
            recovery_func = self.recovery_strategies[strategy_key]
            success = recovery_func(error_context)
            
            if success:
                self.logger.info(f"Recovery successful for {error_key}")
                # Reset error count on successful recovery
                self.error_counts[error_key] = 0
                return True
            else:
                self.logger.warning(f"Recovery failed for {error_key}")
                return False
                
        except Exception as recovery_error:
            self.logger.error(f"Recovery strategy failed: {recovery_error}")
            return False
    
    # Recovery strategy implementations
    def _recover_device_connection(self, error_context: ErrorContext) -> bool:
        """Recover from device connection errors"""
        self.logger.info("Attempting to recover device connection...")
        
        try:
            # Restart ADB server
            subprocess.run(['.scrcpy\\adb', 'kill-server'], 
                         capture_output=True, timeout=10)
            time.sleep(2)
            subprocess.run(['.scrcpy\\adb', 'start-server'], 
                         capture_output=True, timeout=10)
            time.sleep(3)
            
            # Try to connect to default emulator
            result = subprocess.run(['.scrcpy\\adb', 'connect', '127.0.0.1:5554'],
                                  capture_output=True, timeout=10)
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Device connection recovery failed: {e}")
            return False
    
    def _recover_scrcpy_connection(self, error_context: ErrorContext) -> bool:
        """Recover from scrcpy connection errors"""
        self.logger.info("Attempting to recover scrcpy connection...")
        
        try:
            # Kill any existing scrcpy processes
            subprocess.run(['taskkill', '/f', '/im', 'scrcpy.exe'], 
                         capture_output=True)
            time.sleep(2)
            
            # Restart device connection
            return self._recover_device_connection(error_context)
            
        except Exception as e:
            self.logger.error(f"Scrcpy connection recovery failed: {e}")
            return False
    
    def _recover_unit_recognition(self, error_context: ErrorContext) -> bool:
        """Recover from unit recognition errors"""
        self.logger.info("Attempting to recover unit recognition...")
        
        try:
            # Check if units folder exists and has files
            import os
            if not os.path.exists('units') or not os.listdir('units'):
                self.logger.info("Units folder empty, repopulating...")
                # Could trigger unit selection here
                return False
            
            # Check if unit images are valid
            import cv2
            for unit_file in os.listdir('units'):
                img_path = os.path.join('units', unit_file)
                img = cv2.imread(img_path)
                if img is None:
                    self.logger.warning(f"Invalid unit image: {unit_file}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Unit recognition recovery failed: {e}")
            return False
    
    def _recover_screen_capture(self, error_context: ErrorContext) -> bool:
        """Recover from screen capture errors"""
        self.logger.info("Attempting to recover screen capture...")
        
        try:
            import subprocess
            import os
            
            # Step 1: Check if ADB is responsive
            result = subprocess.run(['.scrcpy\\adb', 'devices'], 
                                  capture_output=True, timeout=10, text=True)
            if result.returncode != 0:
                self.logger.error("ADB not responsive")
                return False
            
            # Step 2: Check if device is connected
            if 'emulator-5554' not in result.stdout:
                self.logger.error("Device not connected")
                return False
            
            # Step 3: Try alternative screenshot methods
            methods = [
                # Method 1: Direct screencap to stdout
                ['.scrcpy\\adb', '-s', 'emulator-5554', 'exec-out', 'screencap', '-p'],
                # Method 2: Screencap to device then pull
                ['.scrcpy\\adb', '-s', 'emulator-5554', 'shell', 'screencap', '/sdcard/temp_screenshot.png'],
            ]
            
            for i, method in enumerate(methods, 1):
                self.logger.info(f"Trying screenshot method {i}")
                
                if i == 1:
                    # Direct method
                    try:
                        with open('bot_feed_test_recovery.png', 'wb') as f:
                            result = subprocess.run(method, stdout=f, stderr=subprocess.PIPE, timeout=15)
                        
                        if result.returncode == 0 and os.path.exists('bot_feed_test_recovery.png'):
                            # Verify the file is a valid image
                            import cv2
                            test_img = cv2.imread('bot_feed_test_recovery.png')
                            if test_img is not None:
                                os.remove('bot_feed_test_recovery.png')  # Clean up
                                self.logger.info("Screen capture recovery successful (direct method)")
                                return True
                        
                        if os.path.exists('bot_feed_test_recovery.png'):
                            os.remove('bot_feed_test_recovery.png')
                            
                    except Exception as e:
                        self.logger.warning(f"Direct method failed: {e}")
                        continue
                
                elif i == 2:
                    # Two-step method
                    try:
                        # Step 2a: Take screenshot on device
                        result = subprocess.run(method, capture_output=True, timeout=15)
                        if result.returncode != 0:
                            continue
                        
                        # Step 2b: Pull screenshot from device
                        result = subprocess.run(['.scrcpy\\adb', '-s', 'emulator-5554', 'pull', 
                                               '/sdcard/temp_screenshot.png', 'bot_feed_test_recovery.png'],
                                               capture_output=True, timeout=10)
                        
                        if result.returncode == 0 and os.path.exists('bot_feed_test_recovery.png'):
                            # Verify the file is a valid image
                            import cv2
                            test_img = cv2.imread('bot_feed_test_recovery.png')
                            if test_img is not None:
                                # Clean up
                                os.remove('bot_feed_test_recovery.png')
                                subprocess.run(['.scrcpy\\adb', '-s', 'emulator-5554', 'shell', 
                                              'rm', '/sdcard/temp_screenshot.png'], 
                                              capture_output=True, timeout=5)
                                self.logger.info("Screen capture recovery successful (two-step method)")
                                return True
                        
                        # Clean up on failure
                        if os.path.exists('bot_feed_test_recovery.png'):
                            os.remove('bot_feed_test_recovery.png')
                        subprocess.run(['.scrcpy\\adb', '-s', 'emulator-5554', 'shell', 
                                      'rm', '/sdcard/temp_screenshot.png'], 
                                      capture_output=True, timeout=5)
                        
                    except Exception as e:
                        self.logger.warning(f"Two-step method failed: {e}")
                        continue
            
            self.logger.error("All screenshot recovery methods failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Screen capture recovery failed: {e}")
            return False
    
    def _recover_file_not_found(self, error_context: ErrorContext) -> bool:
        """Recover from file not found errors"""
        self.logger.info("Attempting to recover from file not found...")
        
        # Check if it's a critical file
        error_msg = error_context.error_message.lower()
        
        if 'rank_model.pkl' in error_msg:
            self.logger.error("Critical file rank_model.pkl missing - cannot recover")
            return False
        
        if 'config.ini' in error_msg:
            self.logger.info("Config file missing - will use defaults")
            return True
        
        return True  # Non-critical file missing
    
    def _recover_permission_error(self, error_context: ErrorContext) -> bool:
        """Recover from permission errors"""
        self.logger.info("Attempting to recover from permission error...")
        
        # Log the issue but continue - permission errors are often transient
        self.logger.warning("Permission error detected - check file/folder permissions")
        return True
    
    def _recover_memory_error(self, error_context: ErrorContext) -> bool:
        """Recover from memory errors"""
        self.logger.info("Attempting to recover from memory error...")
        
        try:
            import gc
            gc.collect()  # Force garbage collection
            time.sleep(1)
            return True
            
        except Exception as e:
            self.logger.error(f"Memory recovery failed: {e}")
            return False
    
    def _recover_timeout_error(self, error_context: ErrorContext) -> bool:
        """Recover from timeout errors"""
        self.logger.info("Attempting to recover from timeout error...")
        
        # For timeout errors, we usually just need to wait and retry
        time.sleep(5)
        return True
    
    def register_recovery_strategy(self, error_pattern: str, strategy: Callable):
        """Register a custom recovery strategy"""
        self.recovery_strategies[error_pattern] = strategy
        self.logger.info(f"Registered recovery strategy for: {error_pattern}")
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics"""
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'unique_error_types': len(self.error_counts),
            'error_breakdown': dict(self.error_counts),
            'recent_errors': len([e for e in self.error_history 
                                if time.time() - e.timestamp < 3600])  # Last hour
        }


def with_error_recovery(component: str, error_recovery_system: ErrorRecoverySystem = None):
    """Decorator for adding error recovery to functions"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            recovery_system = error_recovery_system or ErrorRecoverySystem()
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        recovery_system.handle_error(e, component, 
                                                   function=func.__name__,
                                                   attempt=attempt + 1)
                        raise
                    else:
                        # Try to recover
                        if recovery_system.handle_error(e, component,
                                                      function=func.__name__,
                                                      attempt=attempt + 1):
                            continue  # Retry
                        else:
                            raise  # Recovery failed
            
            return None  # Should never reach here
        
        return wrapper
    return decorator


# Global error recovery system
_error_recovery_system = None


def get_error_recovery_system() -> ErrorRecoverySystem:
    """Get the global error recovery system"""
    global _error_recovery_system
    if _error_recovery_system is None:
        _error_recovery_system = ErrorRecoverySystem()
    return _error_recovery_system


if __name__ == '__main__':
    # Test the error recovery system
    recovery_system = ErrorRecoverySystem()
    
    # Simulate an error
    try:
        raise FileNotFoundError("Test file not found")
    except Exception as e:
        recovery_system.handle_error(e, "test_component")
    
    # Print statistics
    stats = recovery_system.get_error_statistics()
    print(f"Error statistics: {stats}")
