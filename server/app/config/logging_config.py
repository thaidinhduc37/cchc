import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .app_config import Config

def setup_logging(config: Config):
    """Setup logging configuration"""
    
    # Create logs directory if not exists
    config.LOG_FILE.parent.mkdir(exist_ok=True)
    
    # Basic configuration
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=10_000_000,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Disable some noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)