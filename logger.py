# logger.py
import os
import logging
from logging.handlers import RotatingFileHandler
import json

# Default logging configuration
DEFAULT_CONFIG = {
    "level": "INFO",
    "file": "logs/pos.log",
    "max_size": 1048576,  # 1MB
    "backup_count": 3
}

# Mapping of string log levels to logging constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def setup_logger(config=None):
    """Set up and configure the application logger."""
    if config is None:
        config = {}
    
    # Merge with default config
    log_config = {**DEFAULT_CONFIG, **config.get("logging", {})}
    
    # Create logger
    logger = logging.getLogger('pos_system')
    
    # Set level
    level = LOG_LEVELS.get(log_config["level"], logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_config["file"])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = RotatingFileHandler(
            log_config["file"],
            maxBytes=log_config["max_size"],
            backupCount=log_config["backup_count"]
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Failed to set up file logging: {str(e)}")
    
    return logger

# Global logger instance
logger = setup_logger()

def configure_logger(config):
    """Reconfigure the logger with new settings."""
    global logger
    
    # Remove existing handlers
    for handler in logger.handlers[:]:  # Make a copy of the list
        logger.removeHandler(handler)
    
    # Set up with new config
    logger = setup_logger(config)
    
    return logger