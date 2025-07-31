#!/usr/bin/env python3
"""
Performance monitoring and metrics collection for Rush Royale Bot
Tracks bot performance, unit recognition accuracy, and system metrics
"""

import time
import threading
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import statistics


@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    timestamp: float
    operation: str
    duration: float
    success: bool
    details: Optional[Dict] = None


class PerformanceMonitor:
    """Performance monitoring system for the bot"""
    
    def __init__(self, log_file: str = "performance.log"):
        self.metrics: List[PerformanceMetrics] = []
        self.log_file = Path(log_file)
        self.lock = threading.Lock()
        self.session_start = time.time()
        
        # Performance thresholds
        self.thresholds = {
            'unit_recognition': 0.1,    # 100ms max for unit recognition
            'screen_capture': 0.05,     # 50ms max for screen capture
            'click_operation': 0.02,    # 20ms max for click
            'grid_analysis': 0.15,      # 150ms max for grid analysis
        }
        
        # Setup logging
        self.logger = logging.getLogger('performance')
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("Performance monitoring initialized")
    
    def record_metric(self, operation: str, duration: float, success: bool = True, **details):
        """Record a performance metric"""
        metric = PerformanceMetrics(
            timestamp=time.time(),
            operation=operation,
            duration=duration,
            success=success,
            details=details if details else None
        )
        
        with self.lock:
            self.metrics.append(metric)
        
        # Check against thresholds
        threshold = self.thresholds.get(operation)
        if threshold and duration > threshold:
            self.logger.warning(
                f"Performance threshold exceeded: {operation} took {duration:.3f}s "
                f"(threshold: {threshold:.3f}s)"
            )
        
        self.logger.info(f"{operation}: {duration:.3f}s ({'✓' if success else '✗'})")
    
    def time_operation(self, operation: str):
        """Context manager for timing operations"""
        return PerformanceTimer(self, operation)
    
    def get_metrics_summary(self, operation: str = None, last_minutes: int = None) -> Dict:
        """Get summary statistics for metrics"""
        with self.lock:
            filtered_metrics = self.metrics.copy()
        
        # Filter by operation
        if operation:
            filtered_metrics = [m for m in filtered_metrics if m.operation == operation]
        
        # Filter by time window
        if last_minutes:
            cutoff_time = time.time() - (last_minutes * 60)
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= cutoff_time]
        
        if not filtered_metrics:
            return {'count': 0}
        
        durations = [m.duration for m in filtered_metrics]
        success_count = sum(1 for m in filtered_metrics if m.success)
        
        return {
            'count': len(filtered_metrics),
            'success_rate': success_count / len(filtered_metrics),
            'avg_duration': statistics.mean(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'median_duration': statistics.median(durations),
            'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
        }
    
    def get_performance_report(self) -> str:
        """Generate a comprehensive performance report"""
        report = []
        report.append("🔍 Performance Monitoring Report")
        report.append("=" * 50)
        
        session_duration = time.time() - self.session_start
        report.append(f"📊 Session Duration: {session_duration / 60:.1f} minutes")
        report.append(f"📈 Total Metrics: {len(self.metrics)}")
        report.append("")
        
        # Summary by operation type
        operations = set(m.operation for m in self.metrics)
        for operation in sorted(operations):
            summary = self.get_metrics_summary(operation)
            if summary['count'] > 0:
                report.append(f"🎯 {operation.replace('_', ' ').title()}:")
                report.append(f"   Count: {summary['count']}")
                report.append(f"   Success Rate: {summary['success_rate']:.1%}")
                report.append(f"   Avg Duration: {summary['avg_duration']:.3f}s")
                report.append(f"   Range: {summary['min_duration']:.3f}s - {summary['max_duration']:.3f}s")
                
                # Check against thresholds
                threshold = self.thresholds.get(operation)
                if threshold:
                    if summary['avg_duration'] > threshold:
                        report.append(f"   ⚠️  Above threshold ({threshold:.3f}s)")
                    else:
                        report.append(f"   ✅ Within threshold ({threshold:.3f}s)")
                report.append("")
        
        # Recent performance (last 10 minutes)
        recent_summary = self.get_metrics_summary(last_minutes=10)
        if recent_summary['count'] > 0:
            report.append("⏱️  Recent Performance (Last 10 minutes):")
            report.append(f"   Operations: {recent_summary['count']}")
            report.append(f"   Success Rate: {recent_summary['success_rate']:.1%}")
            report.append(f"   Avg Duration: {recent_summary['avg_duration']:.3f}s")
        
        return "\n".join(report)
    
    def export_metrics(self, filepath: str = None):
        """Export metrics to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"performance_metrics_{timestamp}.json"
        
        export_data = {
            'session_start': self.session_start,
            'export_time': time.time(),
            'metrics': [asdict(m) for m in self.metrics],
            'thresholds': self.thresholds,
            'summary': self.get_metrics_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Metrics exported to {filepath}")
        return filepath
    
    def clear_old_metrics(self, keep_hours: int = 24):
        """Clear metrics older than specified hours"""
        cutoff_time = time.time() - (keep_hours * 3600)
        
        with self.lock:
            old_count = len(self.metrics)
            self.metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
            removed = old_count - len(self.metrics)
        
        if removed > 0:
            self.logger.info(f"Cleared {removed} old metrics (older than {keep_hours}h)")


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
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
        
        self.monitor.record_metric(
            self.operation, 
            duration, 
            success, 
            **self.details
        )
        
        return False  # Don't suppress exceptions
    
    def set_success(self, success: bool):
        """Manually set operation success status"""
        self.success = success
    
    def add_detail(self, key: str, value):
        """Add detail information to the metric"""
        self.details[key] = value


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def time_function(operation_name: str = None):
    """Decorator for timing function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            monitor = get_performance_monitor()
            
            with monitor.time_operation(op_name) as timer:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    timer.set_success(False)
                    timer.add_detail('error', str(e))
                    raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# Example usage decorators for bot functions
def time_unit_recognition(func):
    """Decorator for timing unit recognition operations"""
    return time_function('unit_recognition')(func)


def time_screen_capture(func):
    """Decorator for timing screen capture operations"""
    return time_function('screen_capture')(func)


def time_click_operation(func):
    """Decorator for timing click operations"""
    return time_function('click_operation')(func)


def time_grid_analysis(func):
    """Decorator for timing grid analysis operations"""
    return time_function('grid_analysis')(func)


if __name__ == '__main__':
    # Test the performance monitoring system
    monitor = get_performance_monitor()
    
    # Simulate some operations
    with monitor.time_operation('test_operation') as timer:
        time.sleep(0.1)
        timer.add_detail('test_param', 'value')
    
    # Generate report
    print(monitor.get_performance_report())
    
    # Export metrics
    filepath = monitor.export_metrics()
    print(f"\nMetrics exported to: {filepath}")
