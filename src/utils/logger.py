# src/utils/logger.py
# ===================
# Purpose: Configure logging for the entire application
# Why: Consistent, structured logging across all modules

import sys
from pathlib import Path
from loguru import logger
from src.config import Config

def setup_logger():
    """
    Setup loguru logger with console and file output
    
    Configures:
    - Console output with colors
    - File output with rotation
    - Proper formatting
    """
    # Remove default handler
    logger.remove()
    
    # Console output with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True
    )
    
    # File output
    log_file = Path(Config.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=Config.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    logger.info("Logger initialized successfully")
    return logger

# Also need to create the __init__.py files if they don't exist

# Example usage:
# from src.utils.logger import setup_logger
# logger = setup_logger()
# logger.info("This is a test log message")