import logging
import time
from threading import Thread, Lock, Event
from typing import Optional, Tuple, Dict, Any, Callable

import cv2
import numpy as np


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