#!/usr/bin/env python3
"""
Rush Royale Bot - Debug Module
Comprehensive debugging and monitoring system
"""

import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import cv2
import numpy as np


class DebugSystem:
    """Comprehensive debugging system for bot operations"""
    
    def __init__(self, enabled: bool = False, debug_dir: str = "debug_output"):
        self.enabled = enabled
        self.debug_dir = Path(debug_dir)
        self.logger = logging.getLogger(__name__)
        
        # Debug data storage
        self.events = []
        self.max_events = 1000
        self.session_start = time.time()
        
        # Performance tracking
        self.performance_data = {}
        
        # Create debug directories
        if self.enabled:
            self._create_debug_dirs()
            self.logger.info("Debug system initialized")
    
    def _create_debug_dirs(self):
        """Create debug output directories"""
        try:
            self.debug_dir.mkdir(exist_ok=True)
            (self.debug_dir / "screenshots").mkdir(exist_ok=True)
            (self.debug_dir / "annotated").mkdir(exist_ok=True)
            (self.debug_dir / "grids").mkdir(exist_ok=True)
            (self.debug_dir / "units").mkdir(exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Could not create debug directories: {e}")
    
    def enable(self):
        """Enable debug mode"""
        self.enabled = True
        self._create_debug_dirs()
        self.log_event("SYSTEM", "debug_enabled", {"timestamp": datetime.now().isoformat()})
        self.logger.info("Debug mode enabled")
    
    def disable(self):
        """Disable debug mode"""
        self.enabled = False
        self.log_event("SYSTEM", "debug_disabled", {"timestamp": datetime.now().isoformat()})
        self.logger.info("Debug mode disabled")
    
    def log_event(self, event_type: str, operation: str, details: Dict[str, Any] = None, 
                  success: bool = True, duration: float = None, warnings: List[str] = None):
        """Log a debug event"""
        if not self.enabled:
            return
        
        event = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'type': event_type,
            'operation': operation,
            'details': details or {},
            'success': success,
            'duration': duration,
            'warnings': warnings or []
        }
        
        self.events.append(event)
        
        # Keep only recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Log to file
        self._log_to_file(event)
    
    def _log_to_file(self, event: Dict):
        """Write event to debug log file"""
        try:
            log_message = f"[{event['type']}] {event['operation']}"
            if event.get('details'):
                log_message += f" | {event['details']}"
            if event.get('warnings'):
                log_message += f" | Warnings: {event['warnings']}"
            
            level = 'WARNING' if event.get('warnings') or not event.get('success') else 'DEBUG'
            self.logger.log(getattr(logging, level), log_message)
            
        except Exception as e:
            self.logger.error(f"Debug logging error: {e}")
    
    def debug_screenshot(self, img, filename: str = None, operation: str = "screenshot") -> str:
        """Save debug screenshot with annotations"""
        if not self.enabled:
            return ""
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_path = self.debug_dir / "screenshots" / filename
            
            # Save screenshot
            success = cv2.imwrite(str(screenshot_path), img)
            
            if success:
                self.log_event("SCREENSHOT", operation, {
                    "filename": filename,
                    "image_shape": list(img.shape) if hasattr(img, 'shape') else [0, 0, 0],
                    "file_size": screenshot_path.stat().st_size if screenshot_path.exists() else 0
                })
                return str(screenshot_path)
            else:
                self.log_event("SCREENSHOT", operation, {
                    "filename": filename,
                    "error": "Failed to save image"
                }, success=False)
                return ""
                
        except Exception as e:
            self.log_event("SCREENSHOT", operation, {
                "error": str(e)
            }, success=False, warnings=[str(e)])
            return ""
    
    def debug_click(self, x: int, y: int, operation: str = "click") -> str:
        """Debug click action with visual annotation"""
        if not self.enabled:
            return ""
        
        try:
            # Create annotated screenshot showing click position
            # This would require access to current screen image
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            filename = f"click_{operation}_{timestamp}.png"
            
            self.log_event("ACTION", "click", {
                "operation": operation,
                "position": [x, y],
                "filename": filename
            })
            
            return filename
            
        except Exception as e:
            self.log_event("ACTION", "click", {
                "error": str(e)
            }, success=False)
            return ""
    
    def debug_recognition(self, unit_name: str, confidence: float, 
                         img_crop = None, position: tuple = None):
        """Debug unit recognition"""
        if not self.enabled:
            return
        
        details = {
            "unit": unit_name,
            "confidence": confidence,
            "position": position
        }
        
        warnings = []
        if confidence < 0.7:
            warnings.append(f"Low confidence recognition: {confidence:.2f}")
        
        # Save unit crop if provided
        if img_crop is not None:
            try:
                timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
                crop_filename = f"unit_{unit_name}_{timestamp}.png"
                crop_path = self.debug_dir / "units" / crop_filename
                
                cv2.imwrite(str(crop_path), img_crop)
                details["crop_saved"] = crop_filename
            except Exception as e:
                warnings.append(f"Could not save unit crop: {e}")
        
        self.log_event("RECOGNITION", "unit_detection", details, 
                      success=(confidence > 0.5), warnings=warnings)
    
    def debug_grid_state(self, grid_df, img = None) -> str:
        """Debug grid state visualization"""
        if not self.enabled:
            return ""
        
        try:
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            filename = f"grid_{timestamp}.png"
            
            # Create grid visualization
            if img is not None:
                # Save annotated grid image
                grid_path = self.debug_dir / "grids" / filename
                cv2.imwrite(str(grid_path), img)
            
            # Log grid state
            grid_summary = self._analyze_grid_state(grid_df)
            
            self.log_event("GRID", "grid_analysis", {
                "filename": filename,
                "grid_summary": grid_summary
            })
            
            return filename
            
        except Exception as e:
            self.log_event("GRID", "grid_analysis", {
                "error": str(e)
            }, success=False)
            return ""
    
    def _analyze_grid_state(self, grid_df) -> Dict:
        """Analyze grid state for debugging"""
        try:
            if grid_df is None or grid_df.empty:
                return {"status": "empty"}
            
            unit_counts = grid_df['unit'].value_counts().to_dict()
            empty_slots = unit_counts.get('empty.png', 0)
            total_units = len(grid_df) - empty_slots
            
            return {
                "total_units": total_units,
                "empty_slots": empty_slots,
                "unit_distribution": unit_counts,
                "grid_utilization": f"{(total_units / len(grid_df) * 100):.1f}%"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def debug_action(self, action_type: str, parameters: Dict[str, Any], 
                    result: Any = None, duration: float = None):
        """Debug bot actions"""
        if not self.enabled:
            return
        
        details = {
            "action_type": action_type,
            "parameters": parameters,
            "result": str(result) if result is not None else None
        }
        
        self.log_event("ACTION", action_type, details, duration=duration)
    
    def debug_performance(self, operation: str, start_time: float, 
                         threshold: float = 1.0) -> float:
        """Debug performance timing"""
        duration = time.time() - start_time
        
        if not self.enabled:
            return duration
        
        # Track performance data
        if operation not in self.performance_data:
            self.performance_data[operation] = []
        
        self.performance_data[operation].append(duration)
        
        # Keep only recent measurements
        if len(self.performance_data[operation]) > 100:
            self.performance_data[operation] = self.performance_data[operation][-100:]
        
        warnings = []
        if duration > threshold:
            warnings.append(f"Slow operation: {duration:.3f}s > {threshold}s threshold")
        
        self.log_event("PERFORMANCE", operation, {
            "duration": duration,
            "threshold": threshold,
            "avg_duration": np.mean(self.performance_data[operation])
        }, warnings=warnings)
        
        return duration
    
    def get_summary(self) -> Dict:
        """Get debug session summary"""
        if not self.enabled:
            return {"debug_enabled": False}
        
        # Calculate statistics
        event_types = {}
        warning_count = 0
        error_count = 0
        
        for event in self.events:
            event_type = event.get('type', 'UNKNOWN')
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            if event.get('warnings'):
                warning_count += len(event['warnings'])
            
            if not event.get('success', True):
                error_count += 1
        
        # Performance summary
        perf_summary = {}
        for operation, durations in self.performance_data.items():
            perf_summary[operation] = {
                "count": len(durations),
                "avg": np.mean(durations),
                "max": np.max(durations),
                "min": np.min(durations)
            }
        
        summary = {
            "debug_enabled": True,
            "session_duration": time.time() - self.session_start,
            "total_events": len(self.events),
            "event_types": event_types,
            "warnings_count": warning_count,
            "errors_count": error_count,
            "performance_summary": perf_summary,
            "last_event": self.events[-1]['operation'] if self.events else None
        }
        
        return summary
    
    def export_session_data(self, output_file: str = None) -> str:
        """Export debug session data to JSON"""
        if not self.enabled:
            return ""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"debug_session_{timestamp}.json"
        
        try:
            export_data = {
                "session_info": {
                    "start_time": self.session_start,
                    "export_time": time.time(),
                    "duration": time.time() - self.session_start
                },
                "summary": self.get_summary(),
                "events": self.events,
                "performance_data": self.performance_data
            }
            
            output_path = self.debug_dir / output_file
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Debug session exported to {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to export debug session: {e}")
            return ""
    
    def clear_events(self):
        """Clear debug events (keep performance data)"""
        if self.enabled:
            self.events.clear()
            self.logger.info("Debug events cleared")
    
    def get_recent_events(self, count: int = 20) -> List[Dict]:
        """Get most recent debug events"""
        return self.events[-count:] if self.events else []
    
    def get_performance_report(self) -> str:
        """Get formatted performance report"""
        if not self.performance_data:
            return "No performance data available"
        
        report = ["Performance Report", "=" * 20]
        
        for operation, durations in self.performance_data.items():
            avg_time = np.mean(durations)
            max_time = np.max(durations)
            count = len(durations)
            
            report.append(f"{operation}:")
            report.append(f"  Count: {count}")
            report.append(f"  Average: {avg_time:.3f}s")
            report.append(f"  Maximum: {max_time:.3f}s")
            report.append("")
        
        return "\n".join(report)


# Global debug instance
_debug_system: Optional[DebugSystem] = None


def get_debug_system() -> DebugSystem:
    """Get global debug system instance"""
    global _debug_system
    
    if _debug_system is None:
        _debug_system = DebugSystem()
    
    return _debug_system


def enable_debug():
    """Enable global debug system"""
    debug_system = get_debug_system()
    debug_system.enable()


def disable_debug():
    """Disable global debug system"""
    debug_system = get_debug_system()
    debug_system.disable()


# Decorator for automatic performance timing
def debug_timing(operation_name: str = None, threshold: float = 1.0):
    """Decorator to automatically time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            debug_system = get_debug_system()
            op_name = operation_name or func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = debug_system.debug_performance(op_name, start_time, threshold)
                return result
            except Exception as e:
                duration = time.time() - start_time
                debug_system.log_event("ERROR", op_name, {
                    "error": str(e),
                    "duration": duration
                }, success=False)
                raise
        
        return wrapper
    return decorator
