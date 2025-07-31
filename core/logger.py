#!/usr/bin/env python3
"""
Rush Royale Bot - Logging System
Centralized logging with file and console output
"""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class BotLogger:
    """Enhanced logging system for the Rush Royale Bot"""
    
    def __init__(self, log_level: str = "INFO", log_file: str = "RR_bot.log", 
                 max_file_size: int = 10*1024*1024, backup_count: int = 5):
        """
        Initialize the logging system
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file
            max_file_size: Maximum log file size in bytes before rotation
            backup_count: Number of backup log files to keep
        """
        self.log_file = Path(log_file)
        self.logger = logging.getLogger('RushRoyaleBot')
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Create formatters
        self.file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        
        # Setup file handler with rotation
        self._setup_file_handler(max_file_size, backup_count)
        
        # Setup console handler
        self._setup_console_handler()
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        self.logger.info("Logging system initialized")
    
    def _setup_file_handler(self, max_size: int, backup_count: int):
        """Setup rotating file handler"""
        try:
            # Ensure log directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            
            file_handler.setFormatter(self.file_formatter)
            file_handler.setLevel(logging.DEBUG)  # File gets all messages
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
    
    def _setup_console_handler(self):
        """Setup console handler"""
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.console_formatter)
            console_handler.setLevel(logging.INFO)  # Console gets INFO and above
            
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup console logging: {e}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)
    
    def log_action(self, action: str, details: Optional[dict] = None):
        """Log bot action with optional details"""
        message = f"ACTION: {action}"
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" ({details_str})"
        
        self.info(message)
    
    def log_combat(self, round_num: int, units_merged: int, mana_used: int):
        """Log combat round information"""
        self.info(f"COMBAT: Round {round_num}, Merged {units_merged} units, Used {mana_used} mana")
    
    def log_recognition(self, unit_name: str, confidence: float, position: tuple):
        """Log unit recognition result"""
        message = f"RECOGNITION: {unit_name} at {position} (confidence: {confidence:.2f})"
        
        if confidence < 0.7:
            self.warning(f"{message} - LOW CONFIDENCE")
        else:
            self.debug(message)
    
    def log_performance(self, operation: str, duration: float, threshold: float = 1.0):
        """Log performance metrics"""
        message = f"PERFORMANCE: {operation} took {duration:.3f}s"
        
        if duration > threshold:
            self.warning(f"{message} - SLOW OPERATION")
        else:
            self.debug(message)
    
    def log_error_recovery(self, error: str, recovery_action: str, success: bool):
        """Log error recovery attempts"""
        status = "SUCCESS" if success else "FAILED"
        self.warning(f"ERROR_RECOVERY: {error} -> {recovery_action} ({status})")
    
    def log_session_start(self, config: dict):
        """Log session start with configuration"""
        self.info("=" * 50)
        self.info("RUSH ROYALE BOT SESSION STARTED")
        self.info("=" * 50)
        
        for key, value in config.items():
            self.info(f"CONFIG: {key} = {value}")
        
        self.info("=" * 50)
    
    def log_session_end(self, duration: float, stats: Optional[dict] = None):
        """Log session end with statistics"""
        self.info("=" * 50)
        self.info(f"SESSION ENDED - Duration: {duration:.1f}s")
        
        if stats:
            self.info("SESSION STATISTICS:")
            for key, value in stats.items():
                self.info(f"  {key}: {value}")
        
        self.info("=" * 50)
    
    def set_level(self, level: str):
        """Change logging level"""
        level_obj = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(level_obj)
        self.info(f"Logging level changed to {level.upper()}")
    
    def add_gui_handler(self, text_widget):
        """Add GUI text widget as log handler"""
        try:
            from .gui_handler import GUIHandler
            gui_handler = GUIHandler(text_widget)
            gui_handler.setFormatter(self.console_formatter)
            gui_handler.setLevel(logging.INFO)
            
            self.logger.addHandler(gui_handler)
            self.info("GUI logging handler added")
            
        except ImportError:
            self.warning("GUI handler not available")
        except Exception as e:
            self.error(f"Failed to add GUI handler: {e}")
    
    def get_recent_logs(self, lines: int = 100) -> list:
        """Get recent log entries from file"""
        try:
            if not self.log_file.exists():
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return f.readlines()[-lines:]
                
        except Exception as e:
            self.error(f"Failed to read recent logs: {e}")
            return []
    
    def export_logs(self, output_file: str, start_time: Optional[datetime] = None, 
                   end_time: Optional[datetime] = None) -> bool:
        """Export logs to file with optional time filtering"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.log_file, 'r', encoding='utf-8') as source:
                with open(output_path, 'w', encoding='utf-8') as target:
                    for line in source:
                        # Simple time filtering (could be enhanced)
                        if start_time or end_time:
                            try:
                                # Extract timestamp from log line
                                timestamp_str = line.split(']')[0][1:]
                                log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                
                                if start_time and log_time < start_time:
                                    continue
                                if end_time and log_time > end_time:
                                    continue
                                    
                            except (ValueError, IndexError):
                                pass  # Include lines without valid timestamps
                        
                        target.write(line)
            
            self.info(f"Logs exported to {output_file}")
            return True
            
        except Exception as e:
            self.error(f"Failed to export logs: {e}")
            return False


class GUIHandler(logging.Handler):
    """Custom logging handler for GUI text widgets"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        """Emit log record to GUI text widget"""
        try:
            message = self.format(record)
            
            # Ensure GUI operations happen on main thread
            self.text_widget.after(0, lambda: self._append_text(message))
            
        except Exception:
            pass  # Silently ignore GUI logging errors
    
    def _append_text(self, message: str):
        """Append text to GUI widget"""
        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', message + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see('end')  # Auto-scroll to bottom
            
        except Exception:
            pass


# Global logger instance
_global_logger: Optional[BotLogger] = None


def get_logger() -> BotLogger:
    """Get global logger instance"""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = BotLogger()
    
    return _global_logger


def setup_logging(log_level: str = "INFO", log_file: str = "RR_bot.log") -> BotLogger:
    """Setup global logging configuration"""
    global _global_logger
    
    _global_logger = BotLogger(log_level=log_level, log_file=log_file)
    return _global_logger
