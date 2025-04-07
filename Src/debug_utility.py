import os
import logging
import sys
import datetime
import traceback
from logging.handlers import RotatingFileHandler

class DebugUtility:
    """
    Advanced debug and logging utility for the Rush Royale Bot.
    Provides various logging levels, log rotation, and error tracking.
    """
    
    def __init__(self, log_dir="logs", max_log_size=5*1024*1024, backup_count=3):
        """
        Initialize the debug utility.
        
        Args:
            log_dir (str): Directory to store log files
            max_log_size (int): Maximum size of log file in bytes before rotation
            backup_count (int): Number of backup log files to keep
        """
        self.log_dir = log_dir
        self.max_log_size = max_log_size
        self.backup_count = backup_count
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Set up logger
        self.logger = logging.getLogger("RR_Bot")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        
        # Create and configure file handler with rotation
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"rr_bot_{timestamp}.log")
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_log_size, 
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Create and configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Error tracking
        self.errors = []
    
    def log_info(self, message):
        """Log info level message"""
        self.logger.info(message)
    
    def log_debug(self, message):
        """Log debug level message"""
        self.logger.debug(message)
    
    def log_warning(self, message):
        """Log warning level message"""
        self.logger.warning(message)
    
    def log_error(self, message, exc_info=False):
        """Log error level message"""
        self.logger.error(message, exc_info=exc_info)
        self.errors.append({"time": datetime.datetime.now(), "message": message})
    
    def log_critical(self, message, exc_info=True):
        """Log critical level message"""
        self.logger.critical(message, exc_info=exc_info)
        self.errors.append({"time": datetime.datetime.now(), "message": message, "critical": True})
    
    def log_exception(self, e, context=""):
        """
        Log an exception with its traceback
        
        Args:
            e (Exception): The exception to log
            context (str): Additional context information
        """
        error_msg = f"{context}: {str(e)}" if context else str(e)
        self.logger.error(f"Exception: {error_msg}")
        self.logger.error(traceback.format_exc())
        self.errors.append({
            "time": datetime.datetime.now(), 
            "message": error_msg,
            "traceback": traceback.format_exc()
        })
    
    def get_recent_errors(self, count=5):
        """Get the most recent errors"""
        return self.errors[-count:] if self.errors else []
    
    def log_screenshot(self, image, prefix="screen"):
        """
        Save a screenshot with timestamp for debugging
        
        Args:
            image: OpenCV image object
            prefix (str): Prefix for the filename
        """
        import cv2
        if not os.path.exists(os.path.join(self.log_dir, "screenshots")):
            os.makedirs(os.path.join(self.log_dir, "screenshots"))
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.log_dir, "screenshots", f"{prefix}_{timestamp}.png")
        
        try:
            cv2.imwrite(filename, image)
            self.logger.debug(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {str(e)}")
            return None