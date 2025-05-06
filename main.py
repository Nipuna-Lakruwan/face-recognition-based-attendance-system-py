import tkinter as tk
import os
import sys
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import application modules
from src.utils import Config, Logger, get_available_cameras, LocalStorage
from src.gui import MainWindow

def main():
    """Main application entry point"""
    # Initialize logger
    logger = Logger.setup()
    logger.info("Starting Face Recognition Attendance System")
    
    # Initialize local storage
    local_storage = LocalStorage()
    logger.info("Local storage initialized for attendance tracking")
    
    # Pre-detect cameras to speed up initialization
    # This helps detect cameras before the GUI is shown
    config = Config()
    if config.get("camera", "detect_cameras", default=True):
        logger.info("Pre-detecting available cameras...")
        available_cameras = get_available_cameras()
        logger.info(f"Detected {len(available_cameras)} camera(s) during initialization")
    
    # Create main window
    root = tk.Tk()
    app = MainWindow(root)
    
    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main()
