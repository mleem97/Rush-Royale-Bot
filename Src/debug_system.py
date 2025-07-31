#!/usr/bin/env python3
"""
Debug System for Rush Royale Bot
Provides comprehensive visibility into bot decision-making, perception, and actions.
Shows what the bot sees, what it decides to do, and warns when things don't go as planned.
"""

import os
import time
import logging
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import cv2
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

# Import performance monitor for safe logging
from performance_monitor import safe_log


@dataclass
class DebugEvent:
    """Data class for debug events"""
    timestamp: float
    event_type: str
    operation: str
    details: Dict[str, Any]
    success: bool
    duration: float = 0.0
    warnings: List[str] = None
    screenshot_path: Optional[str] = None


class DebugVisualizer:
    """Handles visual debugging output and image annotations"""
    
    def __init__(self, debug_dir: str = "debug_output"):
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.debug_dir / "screenshots").mkdir(exist_ok=True)
        (self.debug_dir / "annotated").mkdir(exist_ok=True)
        (self.debug_dir / "grids").mkdir(exist_ok=True)
        (self.debug_dir / "units").mkdir(exist_ok=True)
        
    def save_annotated_screenshot(self, img: np.ndarray, annotations: List[Dict], 
                                 filename: str = None) -> str:
        """Save screenshot with visual annotations"""
        if filename is None:
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            filename = f"debug_{timestamp}.png"
        
        annotated_img = img.copy()
        
        for annotation in annotations:
            ann_type = annotation.get('type', 'point')
            color = annotation.get('color', (0, 255, 0))  # Default green
            
            if ann_type == 'point':
                x, y = annotation['pos']
                cv2.circle(annotated_img, (int(x), int(y)), 8, color, 2)
                if 'label' in annotation:
                    cv2.putText(annotated_img, annotation['label'], 
                              (int(x) + 10, int(y) - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            elif ann_type == 'rectangle':
                x, y, w, h = annotation['rect']
                cv2.rectangle(annotated_img, (int(x), int(y)), 
                            (int(x + w), int(y + h)), color, 2)
                if 'label' in annotation:
                    cv2.putText(annotated_img, annotation['label'], 
                              (int(x), int(y) - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            elif ann_type == 'text':
                x, y = annotation['pos']
                cv2.putText(annotated_img, annotation['text'], 
                          (int(x), int(y)), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        filepath = self.debug_dir / "annotated" / filename
        cv2.imwrite(str(filepath), annotated_img)
        return str(filepath)
    
    def save_grid_visualization(self, grid_df: pd.DataFrame, img: np.ndarray, 
                               filename: str = None) -> str:
        """Create and save grid state visualization"""
        if filename is None:
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            filename = f"grid_{timestamp}.png"
        
        # Create grid visualization
        grid_img = img.copy()
        
        # Get grid coordinates (assuming 3x5 grid)
        from bot_core import get_grid
        boxes, box_size = get_grid()
        
        for idx, row in grid_df.iterrows():
            if idx < len(boxes.flat) // 2:  # Ensure we don't go out of bounds
                grid_pos = row['grid_pos']
                x, y = boxes[grid_pos[0], grid_pos[1]]
                w, h = box_size
                
                # Draw grid cell
                cv2.rectangle(grid_img, (x, y), (x + w, y + h), (255, 255, 255), 1)
                
                # Color code based on unit type
                unit = row.get('unit', 'empty.png')
                rank = row.get('rank', 0)
                
                if unit != 'empty.png':
                    # Green for recognized units, red for empty/unknown
                    color = (0, 255, 0) if rank > 0 else (0, 0, 255)
                    
                    # Fill cell with transparent color
                    overlay = grid_img.copy()
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
                    cv2.addWeighted(grid_img, 0.7, overlay, 0.3, 0, grid_img)
                    
                    # Add unit name and rank
                    unit_name = unit.replace('.png', '').replace('_', ' ')
                    label = f"{unit_name[:8]}\nR{rank}" if rank > 0 else unit_name[:8]
                    
                    # Multi-line text
                    lines = label.split('\n')
                    for i, line in enumerate(lines):
                        cv2.putText(grid_img, line, (x + 5, y + 15 + (i * 15)), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        filepath = self.debug_dir / "grids" / filename
        cv2.imwrite(str(filepath), grid_img)
        return str(filepath)


class DebugSystem:
    """Comprehensive debug system for the Rush Royale Bot"""
    
    def __init__(self, enabled: bool = False, log_file: str = "debug.log"):
        self.enabled = enabled
        self.events: List[DebugEvent] = []
        self.lock = threading.Lock()
        self.log_file = Path(log_file)
        self.visualizer = DebugVisualizer()
        
        # Debug configuration
        self.save_screenshots = True
        self.save_grid_states = True
        self.save_unit_crops = True
        self.max_events = 1000  # Limit memory usage
        
        # Setup debug logger
        self.logger = logging.getLogger('debug')
        if not self.logger.handlers:
            try:
                handler = logging.FileHandler(self.log_file, encoding='utf-8')
            except Exception:
                handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '[%(asctime)s] [DEBUG] %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
        
        # Current state tracking
        self.current_screen_state = None
        self.current_grid_state = None
        self.last_action = None
        self.action_expectations = None
        
        if self.enabled:
            safe_log(self.logger, 'info', "Debug system initialized - Detailed logging ENABLED")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable debug mode"""
        self.enabled = enabled
        if enabled:
            safe_log(self.logger, 'info', "Debug mode ENABLED - All bot actions will be logged")
        else:
            safe_log(self.logger, 'info', "Debug mode DISABLED")
    
    def log_event(self, event_type: str, operation: str, details: Dict[str, Any], 
                  success: bool = True, duration: float = 0.0, 
                  warnings: List[str] = None, screenshot_path: str = None):
        """Log a debug event"""
        if not self.enabled:
            return
        
        event = DebugEvent(
            timestamp=time.time(),
            event_type=event_type,
            operation=operation,
            details=details,
            success=success,
            duration=duration,
            warnings=warnings or [],
            screenshot_path=screenshot_path
        )
        
        with self.lock:
            self.events.append(event)
            # Limit memory usage
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events//2:]
        
        # Log to file
        log_level = 'warning' if warnings or not success else 'info'
        log_msg = f"[{event_type.upper()}] {operation}"
        if details:
            log_msg += f" | Details: {json.dumps(details, default=str)}"
        if warnings:
            log_msg += f" | Warnings: {warnings}"
        
        safe_log(self.logger, log_level, log_msg)
    
    def time_operation(self, operation: str):
        """Context manager for timing operations with debug logging"""
        return DebugTimer(self, operation)
    
    def debug_screen_capture(self, bot, success: bool = True, img: np.ndarray = None):
        """Debug screen capture operation"""
        if not self.enabled:
            return
        
        details = {
            'device': bot.device,
            'bot_id': bot.bot_id,
            'image_shape': img.shape if img is not None else None
        }
        
        warnings = []
        screenshot_path = None
        
        if success and img is not None:
            if img.shape[0] < 100 or img.shape[1] < 100:
                warnings.append(f"Screenshot very small: {img.shape}")
            
            # Save debug screenshot
            if self.save_screenshots:
                timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
                screenshot_path = self.visualizer.debug_dir / "screenshots" / f"capture_{timestamp}.png"
                cv2.imwrite(str(screenshot_path), img)
                details['screenshot_saved'] = str(screenshot_path)
        else:
            warnings.append("Screen capture failed or no image available")
        
        self.log_event("SCREEN_CAPTURE", "getScreen", details, success, 
                      warnings=warnings, screenshot_path=str(screenshot_path) if screenshot_path else None)
    
    def debug_unit_recognition(self, bot, grid_df: pd.DataFrame, img: np.ndarray = None):
        """Debug unit recognition and grid analysis"""
        if not self.enabled:
            return
        
        details = {
            'total_units': len(grid_df),
            'recognized_units': len(grid_df[grid_df['unit'] != 'empty.png']),
            'empty_slots': len(grid_df[grid_df['unit'] == 'empty.png']),
            'unit_distribution': grid_df['unit'].value_counts().to_dict(),
            'rank_distribution': grid_df['rank'].value_counts().to_dict(),
            'average_confidence': grid_df['u_prob'].mean() if 'u_prob' in grid_df.columns else None
        }
        
        warnings = []
        
        # Check for recognition issues
        low_confidence_units = grid_df[grid_df.get('u_prob', 0) > 1500]  # MSE > 1500 is concerning
        if not low_confidence_units.empty:
            warnings.append(f"Low confidence recognition for {len(low_confidence_units)} units")
        
        # Check for inconsistencies
        if self.current_grid_state is not None:
            changed_positions = 0
            for idx, row in grid_df.iterrows():
                if idx < len(self.current_grid_state):
                    old_unit = self.current_grid_state.iloc[idx]['unit']
                    new_unit = row['unit']
                    if old_unit != new_unit and old_unit != 'empty.png' and new_unit != 'empty.png':
                        changed_positions += 1
            
            if changed_positions > 3:  # More than 3 units changed position
                warnings.append(f"Unexpected grid changes: {changed_positions} positions changed")
        
        # Save grid visualization
        screenshot_path = None
        if self.save_grid_states and img is not None:
            screenshot_path = self.visualizer.save_grid_visualization(grid_df, img)
            details['grid_visualization'] = screenshot_path
        
        self.current_grid_state = grid_df.copy()
        
        self.log_event("UNIT_RECOGNITION", "grid_analysis", details, 
                      success=len(warnings) == 0, warnings=warnings, 
                      screenshot_path=screenshot_path)
    
    def debug_action_plan(self, bot, action_type: str, action_details: Dict[str, Any], 
                         expected_outcome: str = None):
        """Debug bot action planning"""
        if not self.enabled:
            return
        
        details = action_details.copy()
        details['expected_outcome'] = expected_outcome
        
        self.last_action = {
            'type': action_type,
            'details': details,
            'timestamp': time.time(),
            'expected_outcome': expected_outcome
        }
        
        self.log_event("ACTION_PLAN", action_type, details)
    
    def debug_action_execution(self, bot, action_type: str, success: bool = True, 
                              actual_outcome: str = None, img: np.ndarray = None):
        """Debug action execution and results"""
        if not self.enabled:
            return
        
        details = {
            'action_type': action_type,
            'actual_outcome': actual_outcome,
            'execution_success': success
        }
        
        warnings = []
        
        # Check if outcome matches expectation
        if (self.last_action and 
            self.last_action.get('expected_outcome') and 
            actual_outcome and 
            self.last_action['expected_outcome'] != actual_outcome):
            warnings.append(
                f"Outcome mismatch: expected '{self.last_action['expected_outcome']}', "
                f"got '{actual_outcome}'"
            )
        
        # Annotate screenshot with action
        screenshot_path = None
        if img is not None and action_type in ['click', 'swipe', 'merge']:
            annotations = []
            
            if action_type == 'click' and self.last_action:
                click_pos = self.last_action['details'].get('position')
                if click_pos:
                    annotations.append({
                        'type': 'point',
                        'pos': click_pos,
                        'color': (0, 255, 0) if success else (0, 0, 255),
                        'label': f"CLICK: {action_type}"
                    })
            
            if annotations:
                screenshot_path = self.visualizer.save_annotated_screenshot(
                    img, annotations, f"action_{action_type}_{int(time.time())}.png"
                )
                details['annotated_screenshot'] = screenshot_path
        
        self.log_event("ACTION_EXECUTION", action_type, details, success, 
                      warnings=warnings, screenshot_path=screenshot_path)
    
    def debug_decision_making(self, bot, decision_context: Dict[str, Any], 
                             chosen_action: str, reasoning: str, alternatives: List[str] = None):
        """Debug bot decision-making process"""
        if not self.enabled:
            return
        
        details = {
            'context': decision_context,
            'chosen_action': chosen_action,
            'reasoning': reasoning,
            'alternatives_considered': alternatives or []
        }
        
        self.log_event("DECISION", "strategy_choice", details)
    
    def debug_error_recovery(self, bot, error: Exception, recovery_action: str, 
                           recovery_success: bool):
        """Debug error recovery attempts"""
        if not self.enabled:
            return
        
        details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'recovery_action': recovery_action,
            'recovery_success': recovery_success
        }
        
        warnings = [f"Error occurred: {error}"]
        if not recovery_success:
            warnings.append(f"Recovery failed: {recovery_action}")
        
        self.log_event("ERROR_RECOVERY", "error_handling", details, 
                      success=recovery_success, warnings=warnings)
    
    def debug_performance_issue(self, bot, operation: str, duration: float, 
                               threshold: float, details: Dict[str, Any] = None):
        """Debug performance issues"""
        if not self.enabled:
            return
        
        perf_details = details or {}
        perf_details.update({
            'operation': operation,
            'duration': duration,
            'threshold': threshold,
            'slowdown_factor': duration / threshold
        })
        
        warnings = [f"Performance threshold exceeded: {duration:.3f}s > {threshold:.3f}s"]
        
        self.log_event("PERFORMANCE", "slow_operation", perf_details, 
                      success=False, warnings=warnings)
    
    def get_debug_summary(self, last_minutes: int = 10) -> Dict[str, Any]:
        """Get debug summary for recent events"""
        if not self.enabled:
            return {'debug_enabled': False}
        
        cutoff_time = time.time() - (last_minutes * 60)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_time]
        
        if not recent_events:
            return {'debug_enabled': True, 'recent_events': 0}
        
        # Categorize events
        event_types = {}
        warnings_count = 0
        errors_count = 0
        
        for event in recent_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            if event.warnings:
                warnings_count += len(event.warnings)
            if not event.success:
                errors_count += 1
        
        return {
            'debug_enabled': True,
            'recent_events': len(recent_events),
            'event_types': event_types,
            'warnings_count': warnings_count,
            'errors_count': errors_count,
            'last_event': recent_events[-1].operation if recent_events else None,
            'current_grid_units': len(self.current_grid_state) if self.current_grid_state is not None else 0
        }
    
    def export_debug_session(self, filepath: str = None) -> str:
        """Export complete debug session data"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"debug_session_{timestamp}.json"
        
        export_data = {
            'session_info': {
                'enabled': self.enabled,
                'total_events': len(self.events),
                'export_time': time.time(),
                'session_duration': self.events[-1].timestamp - self.events[0].timestamp if self.events else 0
            },
            'events': [asdict(event) for event in self.events],
            'summary': self.get_debug_summary(60)  # Last hour
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        safe_log(self.logger, 'info', f"Debug session exported to {filepath}")
        return filepath


class DebugTimer:
    """Context manager for timing operations with debug integration"""
    
    def __init__(self, debug_system: DebugSystem, operation: str):
        self.debug_system = debug_system
        self.operation = operation
        self.start_time = None
        self.success = True
        self.details = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None and self.success
        
        self.debug_system.log_event(
            "PERFORMANCE", self.operation,
            {**self.details, 'duration': duration},
            success, duration
        )
        
        return False  # Don't suppress exceptions
    
    def set_success(self, success: bool):
        """Manually set operation success status"""
        self.success = success
    
    def add_detail(self, key: str, value):
        """Add detail information to the debug log"""
        self.details[key] = value


# Global debug system instance
_debug_system = None


def get_debug_system() -> DebugSystem:
    """Get the global debug system instance"""
    global _debug_system
    if _debug_system is None:
        _debug_system = DebugSystem()
    return _debug_system


def debug_wrapper(event_type: str, operation: str = None):
    """Decorator for debugging function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            debug_sys = get_debug_system()
            if not debug_sys.enabled:
                return func(*args, **kwargs)
            
            op_name = operation or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                debug_sys.log_event(
                    event_type, op_name,
                    {'args_count': len(args), 'kwargs_keys': list(kwargs.keys())},
                    success=True, duration=duration
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                debug_sys.log_event(
                    event_type, op_name,
                    {'error': str(e), 'args_count': len(args)},
                    success=False, duration=duration, warnings=[str(e)]
                )
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# Convenience decorators for common debug operations
def debug_perception(func):
    """Decorator for debugging perception operations"""
    return debug_wrapper('PERCEPTION', 'unit_recognition')(func)


def debug_action(func):
    """Decorator for debugging bot actions"""
    return debug_wrapper('ACTION', 'bot_action')(func)


def debug_screen_analysis(func):
    """Decorator for debugging screen analysis"""
    return debug_wrapper('SCREEN_ANALYSIS', 'screen_operation')(func)


if __name__ == '__main__':
    # Test the debug system
    debug_sys = get_debug_system()
    debug_sys.set_enabled(True)
    
    # Simulate some debug events
    debug_sys.log_event("TEST", "system_test", {"test_param": "value"})
    
    # Generate summary
    summary = debug_sys.get_debug_summary()
    print("Debug Summary:", json.dumps(summary, indent=2))
    
    # Export session
    filepath = debug_sys.export_debug_session()
    print(f"Debug session exported to: {filepath}")
