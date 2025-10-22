"""
Logging utilities
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """Setup structured logging"""
    
    # Create logger
    logger = logging.getLogger('gladly_analyzer')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(f'gladly_analyzer.{name}')


# Default logger instance
logger = get_logger('main')
