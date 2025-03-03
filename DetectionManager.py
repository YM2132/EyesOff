import cv2
import numpy as np
import logging
from threading import Thread, Lock, Event
import time
from typing import Optional, Tuple, Dict, Any, Callable


class DetectionManager:
    """
    Detection manager that shows a privacy alert when unauthorized viewers are detected.
    Supports different detection models and customizable alerts.
    """

    def __init__(self, 
                 face_threshold: int = 1,
                 debounce_time: float = 1.0,
                 alert_duration: Optional[float] = None,
                 alert_color: Tuple[int, int, int] = (0, 0, 255),
                 alert_opacity: float = 0.8,
                 alert_size: Tuple[int, int] = (600, 300),
                 alert_position: str = "center",
                 enable_animations: bool = True):
        """
        Initialize the detection manager.
        
        Args:
            face_threshold: Number of faces that trigger the alert
            debounce_time: Time in seconds to wait before changing alert state
            alert_duration: Optional duration in seconds for the alert (None for manual dismiss)
            alert_color: Alert background color in BGR format
            alert_opacity: Alert opacity (0.0-1.0)
            alert_size: Alert window size (width, height)
            alert_position: Alert position ('center', 'top', 'bottom')
            enable_animations: Whether to enable fade in/out animations
        """
        # Detection settings
        self.face_threshold = face_threshold
        self.debounce_time = debounce_time
        
        # Alert settings
        self.alert_duration = alert_duration
        self.alert_color = alert_color
        self.alert_opacity = max(0.0, min(1.0, alert_opacity))  # Clamp between 0 and 1
        self.alert_size = alert_size
        self.alert_position = alert_position
        self.enable_animations = enable_animations
        
        # State variables
        self.is_alert_showing = False
        self.last_state_change = time.time()
        self.alert_window_name = "PRIVACY ALERT - EYES OFF!!!"
        self.dismiss_event = Event()
        
        # Thread safety
        self.lock = Lock()
        
        # Logging
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Set up logging for the detection manager."""
        logger = logging.getLogger("EyesOff")
        if not logger.handlers:  # Prevent adding duplicate handlers
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def process_detection(self, face_count: int):
        """
        Process the detection result and show/hide warning accordingly.
        
        Args:
            face_count (int): Number of faces detected
        """
        current_time = time.time()
        multiple_viewers_detected = face_count > self.face_threshold
        
        with self.lock:
            time_since_change = current_time - self.last_state_change
            
            # Apply debouncing logic
            if time_since_change < self.debounce_time:
                return
                
            if multiple_viewers_detected and not self.is_alert_showing:
                # Show alert if multiple viewers detected and no alert is currently showing
                self.logger.info(f"Multiple viewers detected ({face_count})! Showing privacy alert.")
                self.last_state_change = current_time
                Thread(target=self._show_privacy_alert, daemon=True).start()
                
            elif not multiple_viewers_detected and self.is_alert_showing:
                # Hide alert if no multiple viewers and alert is showing
                self.logger.info("No unauthorized viewers detected. Hiding alert.")
                self.last_state_change = current_time
                self._dismiss_alert()
    
    def _show_privacy_alert(self):
        """Display a privacy alert using OpenCV with customized settings."""
        try:
            with self.lock:
                if self.is_alert_showing:  # Prevent multiple alerts
                    return
                self.is_alert_showing = True
                self.dismiss_event.clear()
            
            # Create alert image with specified size
            width, height = self.alert_size
            alert_img = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Apply fade-in animation if enabled
            if self.enable_animations:
                self._animate_alert(True, alert_img)
            else:
                # Set solid color background
                alert_img[:] = self.alert_color
                self._draw_alert_text(alert_img)
                
                # Create window and show the alert
                cv2.namedWindow(self.alert_window_name, cv2.WINDOW_NORMAL)
                cv2.setWindowProperty(self.alert_window_name, cv2.WND_PROP_TOPMOST, 1)
                
                # Position the window based on settings
                self._position_window(width, height)
                
                cv2.imshow(self.alert_window_name, alert_img)
            
            # Set up alert duration/dismissal logic
            if self.alert_duration is not None:
                # Auto-dismiss after duration
                if cv2.waitKey(int(self.alert_duration * 1000)) != -1 or self.dismiss_event.wait(self.alert_duration):
                    self._dismiss_alert()
            else:
                # Wait for key press to dismiss
                while not self.dismiss_event.is_set():
                    if cv2.waitKey(100) != -1:  # Check every 100ms
                        self._dismiss_alert()
                        break
            
        except Exception as e:
            self.logger.error(f"Error showing alert: {e}")
            with self.lock:
                self.is_alert_showing = False
    
    def _position_window(self, width: int, height: int):
        """Position the alert window based on settings."""
        # Get screen resolution
        try:
            screen = cv2.getWindowImageRect("dummy")
            cv2.destroyWindow("dummy")
            screen_w, screen_h = screen[2], screen[3]
        except:
            # Fallback to common resolution if can't detect
            screen_w, screen_h = 1920, 1080
        
        if self.alert_position == "top":
            cv2.moveWindow(self.alert_window_name, (screen_w - width) // 2, 50)
        elif self.alert_position == "bottom":
            cv2.moveWindow(self.alert_window_name, (screen_w - width) // 2, screen_h - height - 50)
        else:  # center
            cv2.moveWindow(self.alert_window_name, (screen_w - width) // 2, (screen_h - height) // 2)
    
    def _animate_alert(self, fade_in: bool, alert_img: np.ndarray):
        """Create fade in/out animation effect."""
        width, height = self.alert_size
        steps = 10  # Number of animation steps
        
        # Create window for animation
        cv2.namedWindow(self.alert_window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.alert_window_name, cv2.WND_PROP_TOPMOST, 1)
        self._position_window(width, height)
        
        # Animation loop
        for i in range(steps):
            # Calculate current opacity
            if fade_in:
                current_opacity = (i + 1) / steps * self.alert_opacity
            else:
                current_opacity = (steps - i) / steps * self.alert_opacity
            
            # Create frame with current opacity
            frame = alert_img.copy()
            frame[:] = self.alert_color
            
            # Apply opacity
            if current_opacity < 1.0:
                overlay = frame.copy()
                alpha = current_opacity
                frame = cv2.addWeighted(overlay, alpha, np.zeros_like(frame), 1 - alpha, 0)
            
            # Add text
            self._draw_alert_text(frame)
            
            # Show frame
            cv2.imshow(self.alert_window_name, frame)
            cv2.waitKey(30)  # 30ms delay between frames
    
    def _draw_alert_text(self, img: np.ndarray):
        """Draw warning text on the alert image."""
        height, width, _ = img.shape
        font = cv2.FONT_HERSHEY_DUPLEX
        center_x = width // 2
        
        # Add warning text with centered alignment
        cv2.putText(img, "EYES OFF!!!", 
                   (center_x - 150, height // 3), 
                   font, 2, (255, 255, 255), 4)
                   
        cv2.putText(img, "Privacy Alert", 
                   (center_x - 80, height // 3 + 50), 
                   font, 1, (255, 255, 255), 2)
                   
        cv2.putText(img, "Someone else is looking at your screen!", 
                   (center_x - 220, height // 3 + 100), 
                   font, 0.8, (255, 255, 255), 1)
                   
        cv2.putText(img, "Press any key to dismiss", 
                   (center_x - 120, height // 3 + 150), 
                   font, 0.7, (255, 255, 255), 1)
    
    def _dismiss_alert(self):
        """Dismiss the privacy alert."""
        with self.lock:
            if self.is_alert_showing:
                # Signal the alert thread to stop
                self.dismiss_event.set()
                
                # Apply fade-out animation if enabled
                if self.enable_animations:
                    width, height = self.alert_size
                    alert_img = np.zeros((height, width, 3), dtype=np.uint8)
                    self._animate_alert(False, alert_img)
                
                # Close the window
                cv2.destroyWindow(self.alert_window_name)
                self.is_alert_showing = False
    
    def update_settings(self, settings: Dict[str, Any]):
        """
        Update detection manager settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        with self.lock:
            # Update settings from the dictionary
            if 'face_threshold' in settings:
                self.face_threshold = settings['face_threshold']
            if 'debounce_time' in settings:
                self.debounce_time = settings['debounce_time']
            if 'alert_duration' in settings:
                self.alert_duration = settings['alert_duration']
            if 'alert_color' in settings:
                self.alert_color = settings['alert_color']
            if 'alert_opacity' in settings:
                self.alert_opacity = max(0.0, min(1.0, settings['alert_opacity']))
            if 'alert_size' in settings:
                self.alert_size = settings['alert_size']
            if 'alert_position' in settings:
                self.alert_position = settings['alert_position']
            if 'enable_animations' in settings:
                self.enable_animations = settings['enable_animations']
    
    def stop(self):
        """Stop the detection manager and clean up."""
        self._dismiss_alert()
        cv2.destroyAllWindows()