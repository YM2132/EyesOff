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
    
    def __init__(self, camera_id: int = 0, frame_width: int = 640, frame_height: int = 480):
        """
        Initialize the webcam manager.
        
        Args:
            camera_id: ID of the camera to use
            frame_width: Width to resize captured frames to
            frame_height: Height to resize captured frames to
        """
        super().__init__()
        self.camera_id = camera_id
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cap = None
        self.is_running = False
    
    def start(self) -> bool:
        """
        Start the webcam capture.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.error_occurred.emit(f"Cannot open camera with ID {self.camera_id}")
                return False
                
            # Set capture properties if needed
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            
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
        Read a frame from the webcam.
        
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
            
        # Resize frame if needed
        if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        # Emit the frame for GUI components
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
    
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set the capture resolution.
        
        Args:
            width: Frame width
            height: Frame height
            
        Returns:
            bool: True if resolution changed successfully
        """
        self.frame_width = width
        self.frame_height = height
        
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return True
        return False

    # TODO - MAke use of an actual apple API to check for permissions before we kick off the app. This is a crutch approach which will not holdup, we should wait until user grants access before we start the app. If the user does not grant access we should show them a message
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
