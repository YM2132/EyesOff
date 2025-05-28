"""Abstract base classes for platform-specific operations."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List
from PyQt5.QtWidgets import QWidget


class PlatformNotificationManager(ABC):
    """Abstract base class for platform-specific notifications."""
    
    @abstractmethod
    def show_notification(self, title: str, subtitle: str = "", body: str = "", 
                         sound: Optional[str] = None) -> None:
        """Show a native notification."""
        pass
    
    @abstractmethod
    def request_notification_permission(self) -> None:
        """Request permission to show notifications."""
        pass
    
    @abstractmethod
    def notification_available(self) -> bool:
        """Check if native notifications are available."""
        pass
    
    @abstractmethod
    def configure_alert_sound(self, sound_path: Optional[str]) -> None:
        """Configure the alert sound for notifications."""
        pass


class PlatformAppLauncher(ABC):
    """Abstract base class for launching external applications."""
    
    @abstractmethod
    def launch_app(self, app_path: str) -> bool:
        """Launch an external application."""
        pass
    
    @abstractmethod
    def validate_app_path(self, app_path: str) -> bool:
        """Validate if the path points to a valid application."""
        pass
    
    @abstractmethod
    def get_app_selection_filter(self) -> str:
        """Get file dialog filter for selecting applications."""
        pass
    
    @abstractmethod
    def bring_app_to_front(self, app_name: str) -> bool:
        """Bring an application to the front."""
        pass


class PlatformFileSystem(ABC):
    """Abstract base class for file system operations."""
    
    @abstractmethod
    def get_app_support_directory(self) -> str:
        """Get the application support directory."""
        pass
    
    @abstractmethod
    def get_config_path(self) -> str:
        """Get the configuration file path."""
        pass
    
    @abstractmethod
    def get_snapshots_directory(self) -> str:
        """Get the snapshots directory."""
        pass
    
    @abstractmethod
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure a directory exists, creating it if necessary."""
        pass


class PlatformWindowManager(ABC):
    """Abstract base class for window management."""
    
    @abstractmethod
    def set_window_flags(self, window: QWidget, always_on_top: bool, 
                        frameless: bool) -> None:
        """Set platform-specific window flags."""
        pass
    
    @abstractmethod
    def force_window_to_front(self, window: QWidget) -> None:
        """Force a window to the front across all spaces/desktops."""
        pass
    
    @abstractmethod
    def set_window_level(self, window: QWidget, level: str) -> None:
        """Set the window level (e.g., 'floating', 'modal')."""
        pass
    
    @abstractmethod
    def shake_window(self, window: QWidget) -> None:
        """Perform a platform-specific window shake animation."""
        pass


class PlatformUpdateManager(ABC):
    """Abstract base class for update management."""
    
    @abstractmethod
    def get_update_file_extension(self) -> str:
        """Get the expected update file extension (.dmg, .exe, etc.)."""
        pass
    
    @abstractmethod
    def open_update_file(self, file_path: str) -> bool:
        """Open the update file for installation."""
        pass
    
    @abstractmethod
    def get_installation_instructions(self) -> str:
        """Get platform-specific installation instructions."""
        pass
    
    @abstractmethod
    def validate_update_file(self, file_path: str) -> bool:
        """Validate if the update file is valid for this platform."""
        pass


class PlatformSystemIntegration(ABC):
    """Abstract base class for system integration features."""
    
    @abstractmethod
    def request_accessibility_permission(self) -> bool:
        """Request accessibility permissions if needed."""
        pass
    
    @abstractmethod
    def check_accessibility_permission(self) -> bool:
        """Check if accessibility permissions are granted."""
        pass
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, str]:
        """Get system information for diagnostics."""
        pass
    
    @abstractmethod
    def set_launch_at_startup(self, enabled: bool) -> bool:
        """Enable/disable launch at system startup."""
        pass


class PlatformManager(ABC):
    """Main platform manager that provides access to all platform-specific managers."""
    
    @property
    @abstractmethod
    def notification_manager(self) -> PlatformNotificationManager:
        """Get the notification manager."""
        pass
    
    @property
    @abstractmethod
    def app_launcher(self) -> PlatformAppLauncher:
        """Get the app launcher."""
        pass
    
    @property
    @abstractmethod
    def file_system(self) -> PlatformFileSystem:
        """Get the file system manager."""
        pass
    
    @property
    @abstractmethod
    def window_manager(self) -> PlatformWindowManager:
        """Get the window manager."""
        pass
    
    @property
    @abstractmethod
    def update_manager(self) -> PlatformUpdateManager:
        """Get the update manager."""
        pass
    
    @property
    @abstractmethod
    def system_integration(self) -> PlatformSystemIntegration:
        """Get the system integration manager."""
        pass