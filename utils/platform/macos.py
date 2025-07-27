"""macOS-specific implementations of platform abstractions."""

import os
import sys
import subprocess
import platform
from typing import Optional, Dict
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from .base import (
    PlatformNotificationManager, PlatformAppLauncher, PlatformFileSystem,
    PlatformWindowManager, PlatformUpdateManager, PlatformSystemIntegration,
    PlatformManager
)

# Try to import macOS-specific modules
try:
    import objc
    from AppKit import NSApp, NSRunningApplication, NSWorkspace, NSURL, NSApplicationActivateAllWindows
    from Foundation import (NSFileManager, NSSearchPathForDirectoriesInDomains,
                            NSApplicationSupportDirectory, NSUserDomainMask, NSLog,
                            )
    MACOS_APIS_AVAILABLE = True
except ImportError:
    MACOS_APIS_AVAILABLE = False


class MacOSNotificationManager(PlatformNotificationManager):
    """macOS implementation of notification manager."""
    
    def __init__(self):
        self._permission_requested = False
        self._sound_path = None
    
    def show_notification(self, title: str, subtitle: str = "", body: str = "",
                         sound: Optional[str] = None) -> None:
        """Show a native macOS notification using osascript."""
        if not self.notification_available():
            return
        
        # Skip notifications when not running from app bundle
        if not self._is_running_from_app_bundle():
            print(f"[Platform] Skipping notification (not running from app bundle): {title} - {body}")
            return

        # Try native notification first
        if MACOS_APIS_AVAILABLE:
            try:
                from Foundation import NSUserNotification, NSUserNotificationCenter

                # Create notification
                notification = NSUserNotification.alloc().init()
                notification.setTitle_(title)
                if subtitle:
                    notification.setSubtitle_(subtitle)
                notification.setInformativeText_(body)

                # Set sound
                if sound:
                    notification.setSoundName_(sound)
                else:
                    notification.setSoundName_(None)  # Silent

                # Deliver via notification center
                center = NSUserNotificationCenter.defaultUserNotificationCenter()
                center.deliverNotification_(notification)

                NSLog(f"PYQT: Delivered native notification: {title}")
                return
            except Exception as e:
                NSLog(f"PYQT: Failed to show native notification: {e}")

            # Don't fall back to osascript - it shows alerts!
            print(f"[Platform] Native notifications not available")

    def request_notification_permission(self) -> None:
        """Request notification permissions on macOS."""
        if not self._is_running_from_app_bundle():
            return

        # macOS will handle permissions when we try to show a native notification
        self._permission_requested = True
    
    def notification_available(self) -> bool:
        """Check if notifications are available on macOS."""
        return platform.system() == 'Darwin'
    
    def configure_alert_sound(self, sound_path: Optional[str]) -> None:
        """Configure the alert sound for notifications."""
        self._sound_path = sound_path
    
    def _is_running_from_app_bundle(self) -> bool:
        """Check if we're running from a macOS .app bundle."""
        try:
            # Check if we're inside a .app bundle
            bundle_path = os.path.abspath(sys.executable)
            return '.app/Contents/MacOS' in bundle_path
        except:
            return False


class MacOSAppLauncher(PlatformAppLauncher):
    """macOS implementation of app launcher."""
    
    def launch_app(self, app_path: str) -> bool:
        """Launch a macOS application."""
        if not self.validate_app_path(app_path):
            return False
            
        try:
            if MACOS_APIS_AVAILABLE:
                # Try using NSWorkspace first
                workspace = NSWorkspace.sharedWorkspace()
                url = NSURL.fileURLWithPath_(app_path)
                
                # Check if app is already running
                bundle_id = self._get_bundle_id(app_path)
                if bundle_id:
                    running_apps = workspace.runningApplications()
                    for app in running_apps:
                        if app.bundleIdentifier() == bundle_id:
                            # App is running, activate it
                            app.activateWithOptions_(NSApplicationActivateAllWindows)
                            return True
                
                # Launch the app
                config = workspace.configurationForOpeningURL_options_(url, 0)
                app, error = workspace.openURL_configuration_error_(url, config, None)
                return app is not None
            else:
                # Fallback to subprocess
                subprocess.Popen(['open', app_path])
                return True
        except Exception:
            # Final fallback
            try:
                subprocess.Popen(['open', app_path])
                return True
            except:
                return False
    
    def validate_app_path(self, app_path: str) -> bool:
        """Check if path is a valid macOS application."""
        if not app_path:
            return False
        path = Path(app_path)
        return path.exists() and path.suffix == '.app'
    
    def get_app_selection_filter(self) -> str:
        """Get file dialog filter for macOS applications."""
        return "Applications (*.app)"
    
    def bring_app_to_front(self, app_name: str) -> bool:
        """Bring an application to the front using various methods."""
        try:
            # Method 1: Try AppleScript
            script = f'''
            tell application "{app_name}"
                activate
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return True
        except:
            pass
        
        # Method 2: Try clicking dock icon
        try:
            script = f'''
            tell application "System Events"
                tell process "Dock"
                    set frontmost to true
                    click UI element "{app_name}" of list 1
                end tell
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return True
        except:
            pass
        
        return False
    
    def _get_bundle_id(self, app_path: str) -> Optional[str]:
        """Get bundle identifier from app path."""
        try:
            plist_path = Path(app_path) / "Contents" / "Info.plist"
            if plist_path.exists():
                result = subprocess.run(
                    ['defaults', 'read', str(plist_path), 'CFBundleIdentifier'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        return None


class MacOSFileSystem(PlatformFileSystem):
    """macOS implementation of file system operations."""
    
    def get_app_support_directory(self) -> str:
        """Get the Application Support directory for macOS."""
        if MACOS_APIS_AVAILABLE:
            try:
                paths = NSSearchPathForDirectoriesInDomains(
                    NSApplicationSupportDirectory,
                    NSUserDomainMask,
                    True
                )
                if paths:
                    app_support = paths[0]
                    eyesoff_dir = os.path.join(app_support, "EyesOff")
                    self.ensure_directory_exists(eyesoff_dir)
                    return eyesoff_dir
            except:
                pass
        
        # Fallback
        home = os.path.expanduser("~")
        app_support = os.path.join(home, "Library", "Application Support", "EyesOff")
        self.ensure_directory_exists(app_support)
        return app_support
    
    def get_config_path(self) -> str:
        """Get the configuration file path."""
        return os.path.join(self.get_app_support_directory(), "config.yaml")
    
    def get_snapshots_directory(self) -> str:
        """Get the snapshots directory."""
        snapshots_dir = os.path.join(self.get_app_support_directory(), "face_snapshots")
        self.ensure_directory_exists(snapshots_dir)
        return snapshots_dir
    
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure a directory exists."""
        os.makedirs(path, exist_ok=True)


class MacOSWindowManager(PlatformWindowManager):
    """macOS implementation of window management."""
    
    def set_window_flags(self, window: QWidget, always_on_top: bool, 
                        frameless: bool) -> None:
        """Set window flags for macOS."""
        flags = Qt.WindowType.Window
        
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        
        if frameless:
            flags |= Qt.WindowType.FramelessWindowHint
            
        window.setWindowFlags(flags)
    
    def force_window_to_front(self, window: QWidget) -> None:
        """Force window to front on macOS."""
        window.raise_()
        window.activateWindow()
        
        if MACOS_APIS_AVAILABLE and NSApp:
            # Use macOS API to ensure window comes to front
            NSApp.activateIgnoringOtherApps_(True)
    
    def set_window_level(self, window: QWidget, level: str) -> None:
        """Set window level on macOS."""
        # Qt handles most of this through window flags
        if level == 'floating':
            self.set_window_flags(window, always_on_top=True, frameless=False)
        elif level == 'modal':
            window.setWindowModality(Qt.WindowModality.ApplicationModal)
    
    def shake_window(self, window: QWidget) -> None:
        """Perform macOS window shake animation."""
        # Note: This would require Core Animation
        # For now, we'll use Qt's move to simulate a simple shake
        original_pos = window.pos()
        for i in range(3):
            window.move(original_pos.x() - 10, original_pos.y())
            window.repaint()
            window.move(original_pos.x() + 10, original_pos.y())
            window.repaint()
        window.move(original_pos)


class MacOSUpdateManager(PlatformUpdateManager):
    """macOS implementation of update management."""
    
    def get_update_file_extension(self) -> str:
        """Get DMG extension for macOS."""
        return ".dmg"
    
    def open_update_file(self, file_path: str) -> bool:
        """Open DMG file for installation."""
        try:
            subprocess.Popen(['open', file_path])
            return True
        except:
            return False
    
    def get_installation_instructions(self) -> str:
        """Get macOS installation instructions."""
        return (
            "The update DMG has been opened. Please:\n"
            "1. Drag EyesOff to your Applications folder\n"
            "2. Replace the existing version when prompted\n"
            "3. Restart EyesOff after installation"
        )
    
    def validate_update_file(self, file_path: str) -> bool:
        """Validate DMG file."""
        return file_path.endswith('.dmg') and os.path.exists(file_path)


class MacOSSystemIntegration(PlatformSystemIntegration):
    """macOS implementation of system integration."""
    
    def request_accessibility_permission(self) -> bool:
        """Request accessibility permissions on macOS."""
        # This typically requires showing system preferences
        try:
            subprocess.run([
                'osascript', '-e',
                'tell application "System Preferences" to reveal anchor "Privacy_Accessibility" of pane "com.apple.preference.security"'
            ])
            subprocess.run([
                'osascript', '-e',
                'tell application "System Preferences" to activate'
            ])
            return True
        except:
            return False
    
    def check_accessibility_permission(self) -> bool:
        """Check if accessibility permissions are granted."""
        # This would require checking system accessibility API
        # For now, return True as we assume permissions are handled
        return True
    
    def get_system_info(self) -> Dict[str, str]:
        """Get macOS system information."""
        info = {
            'platform': 'macOS',
            'version': platform.mac_ver()[0],
            'architecture': platform.machine(),
            'python_version': sys.version
        }
        return info
    
    def set_launch_at_startup(self, enabled: bool) -> bool:
        """Enable/disable launch at startup on macOS."""
        # This would require LaunchServices API
        # For now, return False indicating not implemented
        return False


class MacOSPlatformManager(PlatformManager):
    """Main macOS platform manager."""
    
    def __init__(self):
        self._notification_manager = MacOSNotificationManager()
        self._app_launcher = MacOSAppLauncher()
        self._file_system = MacOSFileSystem()
        self._window_manager = MacOSWindowManager()
        self._update_manager = MacOSUpdateManager()
        self._system_integration = MacOSSystemIntegration()
    
    @property
    def notification_manager(self) -> PlatformNotificationManager:
        return self._notification_manager
    
    @property
    def app_launcher(self) -> PlatformAppLauncher:
        return self._app_launcher
    
    @property
    def file_system(self) -> PlatformFileSystem:
        return self._file_system
    
    @property
    def window_manager(self) -> PlatformWindowManager:
        return self._window_manager
    
    @property
    def update_manager(self) -> PlatformUpdateManager:
        return self._update_manager
    
    @property
    def system_integration(self) -> PlatformSystemIntegration:
        return self._system_integration