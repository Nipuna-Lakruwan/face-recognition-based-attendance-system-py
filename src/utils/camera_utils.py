import cv2
import logging

def get_available_cameras(max_cameras=10):
    """
    Detect available cameras on the system.
    
    Args:
        max_cameras (int): Maximum number of cameras to check for
        
    Returns:
        list: List of tuples (index, status) of available cameras
    """
    logger = logging.getLogger("attendance_system")
    logger.info("Scanning for available cameras...")
    
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # Camera works and returns frames
                camera_name = f"Camera {i}"
                # Try to get camera name (works on some systems)
                try:
                    camera_name = cap.getBackendName()
                except:
                    pass
                
                logger.info(f"Found camera at index {i}: {camera_name}")
                available_cameras.append((i, camera_name))
            cap.release()
    
    if not available_cameras:
        logger.warning("No cameras detected")
    else:
        logger.info(f"Found {len(available_cameras)} camera(s)")
        
    return available_cameras
