import os
import json
from typing import Dict, Any, Optional
from PyQt5.QtCore import QSettings


class ConfigManager:
    """
    Manages application configuration using QSettings and JSON.
    Provides functions to load, save, and access configuration settings.
    """
    
    def __init__(self, organization: str = "EyesOffApp", application: str = "EyesOff"):
        """
        Initialize the configuration manager.
        
        Args:
            organization: Organization name for QSettings
            application: Application name for QSettings
        """
        self.settings = QSettings(organization, application)
        self.config_file = os.path.expanduser("~/.eyesoff/config.json")
        self.default_config = self._get_default_config()
        self.current_config = self.default_config.copy()
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Load configuration from files and settings
        self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Dict: Default configuration settings
        """
        return {
            # Detector settings
            "detector_type": "yunet",
            "model_path": "./models/face_detection_yunet_2023mar.onnx",
            "confidence_threshold": 0.75,
            "face_threshold": 1,
            
            # Camera settings
            "camera_id": 0,
            "frame_width": 640,
            "frame_height": 480,
            
            # Alert settings
            "alert_on": False,  # alert is deactivated by default
            "alert_duration": None,  # None for manual dismiss
            "alert_color": (0, 0, 255),  # BGR Red
            "alert_opacity": 0.8,
            "alert_size": (600, 300),
            "alert_position": "center",
            "enable_animations": True,
            "alert_sound_enabled": False,
            "alert_sound_file": "",
            "alert_text": "EYES OFF!!!",
            "fullscreen_mode": False,  # Whether to show alert in fullscreen
            
            # Application settings
            "debounce_time": 1.0,
            "start_minimized": False,
            "minimize_to_tray": True,
            "start_on_boot": False,
            "always_on_top": False,
            "show_detection_visualization": True,
            "privacy_mode": False,  # Blur faces in UI
            
            # UI settings
            "theme": "system",  # system, light, dark
            "ui_scale": 1.0,
            "language": "en",
        }
    
    def _load_config(self):
        """Load configuration from QSettings and config file."""
        # Try to load from JSON file first
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.current_config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {e}")
        
        # Load values from QSettings, overriding file settings
        for key in self.default_config.keys():
            if self.settings.contains(key):
                value = self.settings.value(key)
                # Convert to the appropriate type based on default value
                if isinstance(self.default_config[key], bool):
                    value = bool(value) if value in (True, False) else value == "true"
                elif isinstance(self.default_config[key], int):
                    value = int(value)
                elif isinstance(self.default_config[key], float):
                    value = float(value)
                
                self.current_config[key] = value
    
    def save_config(self):
        """Save the current configuration to both QSettings and JSON file."""
        # Save to QSettings
        for key, value in self.current_config.items():
            self.settings.setValue(key, value)
        
        # Save to JSON file
        try:
            with open(self.config_file, 'w') as f:
                # Convert tuple values to lists for JSON serialization
                json_config = {}
                for key, value in self.current_config.items():
                    if isinstance(value, tuple):
                        json_config[key] = list(value)
                    else:
                        json_config[key] = value
                
                json.dump(json_config, f, indent=4)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self.current_config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.current_config[key] = value
        # Save immediately for persistence
        self.settings.setValue(key, value)
    
    def update(self, config_dict: Dict[str, Any]):
        """
        Update multiple configuration values.
        
        Args:
            config_dict: Dictionary of configuration values
        """
        self.current_config.update(config_dict)
        # Save each value to QSettings
        for key, value in config_dict.items():
            self.settings.setValue(key, value)
    
    def reset_to_defaults(self):
        """Reset all configuration to default values."""
        self.current_config = self.default_config.copy()
        
        # Clear QSettings
        self.settings.clear()
        
        # Save defaults to both QSettings and file
        self.save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dict: All configuration values
        """
        return self.current_config.copy()