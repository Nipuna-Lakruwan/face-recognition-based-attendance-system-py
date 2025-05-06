import logging
import os
from datetime import datetime
from pathlib import Path
from .config import Config

class Logger:
    """Logger setup for the application"""
    
    @staticmethod
    def setup():
        """Set up the application logger"""
        config = Config()
        log_dir = Path(config.get("paths", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"attendance_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Configure logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger("attendance_system")
