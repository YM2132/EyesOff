from typing import Tuple, Optional

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


class WebcamManager(QObject):
    """
    Manages webcam access and frame capture with PyQt integration.
    Emits signals when frames are captured for GUI components to use.
    """
    # Signal emitted when a new frame is available
    frame_ready = pyqtSignal(np.ndarray)
    # Signal emitted when an error occurs
    error_occurred = pyqtSignal(str)
    
    def __init__(self, camera_id: int = 0):
        """
        Initialize the webcam manager.
        
        Args:
            camera_id: ID of the camera to use
        """
        super().__init__()
        self.camera_id = camera_id
        self.frame_width = None
        self.frame_height = None
        self.cap = None
        self.is_running = False
        self.available_resolutions = []
    
    def start(self) -> bool:
        """
        Start the webcam capture at highest available resolution.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.error_occurred.emit(f"Cannot open camera with ID {self.camera_id}")
                return False
            
            # Detect available resolutions
            self._detect_available_resolutions()
            
            # Use the highest available resolution
            if self.available_resolutions:
                # Get the highest resolution (last in sorted list)
                best_width, best_height = self.available_resolutions[-1]
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, best_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, best_height)
                
                # Verify actual resolution set
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                print(f"Camera initialized at highest resolution: {self.frame_width}x{self.frame_height}")
            else:
                # Fallback to current resolution if detection failed
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Using default camera resolution: {self.frame_width}x{self.frame_height}")
            
            # Optimize camera settings for better quality
            self.optimize_camera_settings()
            
            self.is_running = True
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error starting webcam: {e}")
            return False
    
    def stop(self):
        """Stop the webcam capture."""
        self.is_running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a frame from the webcam at full resolution.
        
        Returns:
            Tuple containing:
                - Success flag
                - Frame (if successful) or None (if failed)
        """
        if not self.is_running or not self.cap or not self.cap.isOpened():
            return False, None
            
        success, frame = self.cap.read()
        if not success:
            return False, None
        
        # Always return full resolution frame - let display layer handle scaling
        self.frame_ready.emit(frame)
        
        return True, frame
    
    def set_camera(self, camera_id: int) -> bool:
        """
        Change the active camera.
        
        Args:
            camera_id: ID of the camera to use
            
        Returns:
            bool: True if camera changed successfully, False otherwise
        """
        was_running = self.is_running
        
        # Stop the current camera if running
        if was_running:
            self.stop()
        
        # Update camera ID
        self.camera_id = camera_id
        
        # Restart if it was running
        if was_running:
            return self.start()
        return True
    

    @staticmethod
    def get_device_list(max_retries=5, retry_delay=1.0) -> list:
        """
        Get a list of available camera devices with retry mechanism.

        Args:
            max_retries: Maximum number of retries if no cameras are found
            retry_delay: Delay between retries in seconds

        Returns:
            list: List of available camera device IDs
        """
        retry_count = 0
        available_cameras = []

        while retry_count <= max_retries:
            # Check the first 10 camera indices
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()

            # If we found cameras, return the list
            if available_cameras:
                return available_cameras

            # No cameras found, increment retry count
            retry_count += 1

            # Only wait and retry if we haven't hit the maximum
            if retry_count <= max_retries:
                print(f"No cameras found, retrying ({retry_count}/{max_retries})...")
                import time
                time.sleep(retry_delay)

        # If we get here, we've exhausted all retries
        print("Failed to find any camera devices after maximum retries")
        return available_cameras  # Will be empty
    
    def _detect_available_resolutions(self):
        """Detect resolutions supported by the current camera."""
        if not self.cap or not self.cap.isOpened():
            return
        
        # Key resolutions to test (simplified list for speed)
        test_resolutions = [
            (3840, 2160),   # 4K
            (2560, 1440),   # QHD
            (1920, 1080),   # Full HD
            (1280, 720),    # HD
            (640, 480),     # VGA (fallback)
        ]
        
        self.available_resolutions = []
        original_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        original_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        # Add current resolution first
        current_res = (int(original_width), int(original_height))
        if current_res not in test_resolutions:
            test_resolutions.insert(0, current_res)
        
        for width, height in test_resolutions:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width == width and actual_height == height:
                if (width, height) not in self.available_resolutions:
                    self.available_resolutions.append((width, height))
        
        # Sort by total pixels (width * height)
        self.available_resolutions.sort(key=lambda r: r[0] * r[1])
        
        print(f"Available resolutions: {self.available_resolutions}")
    
    
    def optimize_camera_settings(self):
        """Optimize camera settings for better quality - FaceTime style."""
        if not self.cap or not self.cap.isOpened():
            return
        
        try:
            # Try to set camera properties for better quality
            # Note: Not all cameras support all properties
            
            # Set higher FPS if supported (60 fps for smooth video if available)
            self.cap.set(cv2.CAP_PROP_FPS, 60)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if actual_fps < 60:
                self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Enable auto-exposure for better lighting adaptation
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)  # 3 = auto mode
            
            # Set buffer size to 1 for minimal latency (real-time feel)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Disable auto white balance and set it manually for consistency
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 1)  # Enable auto white balance
            
            # Try to improve image quality settings
            # These may not work on all cameras but won't cause errors
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)  # Default brightness
            self.cap.set(cv2.CAP_PROP_CONTRAST, 0.5)    # Default contrast
            self.cap.set(cv2.CAP_PROP_SATURATION, 0.65) # Slightly enhanced saturation
            self.cap.set(cv2.CAP_PROP_SHARPNESS, 0.7)   # Slight sharpness boost
            self.cap.set(cv2.CAP_PROP_GAIN, 0.5)        # Moderate gain
            
            # Try to set codec to MJPEG for better quality (if supported)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            # Set auto-focus if available
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            print("Camera settings optimized for FaceTime-like quality")
        except Exception as e:
            print(f"Note: Some camera optimizations may not be supported: {e}")
