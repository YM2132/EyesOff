"""Windows-specific implementations of platform abstractions."""

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


class WindowsNotificationManager(PlatformNotificationManager):
    """Windows implementation of notification manager."""
    
    def __init__(self):
        self._sound_path = None
        # Try to import Windows notification library
        try:
            from plyer import notification
            self._plyer_available = True
            self._notification = notification
        except ImportError:
            self._plyer_available = False
            self._notification = None
    
    def show_notification(self, title: str, subtitle: str = "", body: str = "", 
                         sound: Optional[str] = None) -> None:
        """Show a native Windows notification."""
        if not self.notification_available():
            return
        
        # Combine subtitle and body for Windows
        message = f"{subtitle}\n{body}" if subtitle else body
        
        if self._plyer_available and self._notification:
            try:
                self._notification.notify(
                    title=title,
                    message=message,
                    app_name='EyesOff',
                    timeout=10
                )
            except:
                pass
        else:
            # Fallback: Use Windows MSG command (basic)
            try:
                subprocess.run(
                    ['msg', '*', f'/TIME:10', f'{title}: {message}'],
                    check=False,
                    capture_output=True
                )
            except:
                pass
    
    def request_notification_permission(self) -> None:
        """Windows doesn't require explicit notification permissions."""
        pass
    
    def notification_available(self) -> bool:
        """Check if notifications are available on Windows."""
        return platform.system() == 'Windows'
    
    def configure_alert_sound(self, sound_path: Optional[str]) -> None:
        """Configure the alert sound for notifications."""
        self._sound_path = sound_path


class WindowsAppLauncher(PlatformAppLauncher):
    """Windows implementation of app launcher."""
    
    def launch_app(self, app_path: str) -> bool:
        """Launch a Windows application."""
        if not self.validate_app_path(app_path):
            return False
        
        try:
            # Use os.startfile for Windows
            os.startfile(app_path)
            return True
        except OSError:
            # Fallback to subprocess
            try:
                subprocess.Popen([app_path])
                return True
            except:
                return False
    
    def validate_app_path(self, app_path: str) -> bool:
        """Check if path is a valid Windows executable."""
        if not app_path:
            return False
        path = Path(app_path)
        return path.exists() and path.suffix.lower() in ['.exe', '.bat', '.cmd']
    
    def get_app_selection_filter(self) -> str:
        """Get file dialog filter for Windows applications."""
        return "Executables (*.exe);;All Files (*.*)"
    
    def bring_app_to_front(self, app_name: str) -> bool:
        """Bring an application to the front on Windows."""
        try:
            # Use PowerShell to bring window to front
            ps_script = f'''
            $app = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{app_name}*"}} | Select-Object -First 1
            if ($app) {{
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {{
                        [DllImport("user32.dll")]
                        public static extern bool SetForegroundWindow(IntPtr hWnd);
                        [DllImport("user32.dll")]
                        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    }}
"@
                [Win32]::ShowWindow($app.MainWindowHandle, 9)
                [Win32]::SetForegroundWindow($app.MainWindowHandle)
                $true
            }} else {{
                $false
            }}
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'True' in result.stdout
        except:
            return False


class WindowsFileSystem(PlatformFileSystem):
    """Windows implementation of file system operations."""
    
    def get_app_support_directory(self) -> str:
        """Get the Application Data directory for Windows."""
        # Use APPDATA environment variable
        appdata = os.environ.get('APPDATA')
        if not appdata:
            appdata = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
        
        eyesoff_dir = os.path.join(appdata, 'EyesOff')
        self.ensure_directory_exists(eyesoff_dir)
        return eyesoff_dir
    
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


class WindowsWindowManager(PlatformWindowManager):
    """Windows implementation of window management."""
    
    def set_window_flags(self, window: QWidget, always_on_top: bool, 
                        frameless: bool) -> None:
        """Set window flags for Windows."""
        flags = Qt.WindowType.Window
        
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        
        if frameless:
            flags |= Qt.WindowType.FramelessWindowHint
            
        window.setWindowFlags(flags)
    
    def force_window_to_front(self, window: QWidget) -> None:
        """Force window to front on Windows."""
        window.raise_()
        window.activateWindow()
        
        # Windows-specific: minimize and restore to force to front
        window.showMinimized()
        window.showNormal()
        window.raise_()
        window.activateWindow()
    
    def set_window_level(self, window: QWidget, level: str) -> None:
        """Set window level on Windows."""
        if level == 'floating':
            self.set_window_flags(window, always_on_top=True, frameless=False)
        elif level == 'modal':
            window.setWindowModality(Qt.WindowModality.ApplicationModal)
    
    def shake_window(self, window: QWidget) -> None:
        """Perform Windows window shake animation."""
        # Simple shake animation using Qt
        original_pos = window.pos()
        for i in range(3):
            window.move(original_pos.x() - 5, original_pos.y())
            QWidget.repaint(window)
            window.move(original_pos.x() + 5, original_pos.y())
            QWidget.repaint(window)
        window.move(original_pos)


class WindowsUpdateManager(PlatformUpdateManager):
    """Windows implementation of update management."""
    
    def get_update_file_extension(self) -> str:
        """Get EXE extension for Windows."""
        return ".exe"
    
    def open_update_file(self, file_path: str) -> bool:
        """Open EXE file for installation."""
        try:
            os.startfile(file_path)
            return True
        except:
            try:
                subprocess.Popen([file_path])
                return True
            except:
                return False
    
    def get_installation_instructions(self) -> str:
        """Get Windows installation instructions."""
        return (
            "The update installer has been opened. Please:\n"
            "1. Follow the installation wizard\n"
            "2. Close EyesOff before continuing if prompted\n"
            "3. Restart EyesOff after installation completes"
        )
    
    def validate_update_file(self, file_path: str) -> bool:
        """Validate EXE/MSI file."""
        return (file_path.endswith(('.exe', '.msi')) and 
                os.path.exists(file_path))


class WindowsSystemIntegration(PlatformSystemIntegration):
    """Windows implementation of system integration."""
    
    def request_accessibility_permission(self) -> bool:
        """Windows doesn't require explicit accessibility permissions."""
        return True
    
    def check_accessibility_permission(self) -> bool:
        """Windows doesn't require explicit accessibility permissions."""
        return True
    
    def get_system_info(self) -> Dict[str, str]:
        """Get Windows system information."""
        info = {
            'platform': 'Windows',
            'version': platform.version(),
            'architecture': platform.machine(),
            'python_version': sys.version
        }
        return info
    
    def set_launch_at_startup(self, enabled: bool) -> bool:
        """Enable/disable launch at startup on Windows."""
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "EyesOff"
            exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                               winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
            return True
        except:
            return False


class WindowsPlatformManager(PlatformManager):
    """Main Windows platform manager."""
    
    def __init__(self):
        self._notification_manager = WindowsNotificationManager()
        self._app_launcher = WindowsAppLauncher()
        self._file_system = WindowsFileSystem()
        self._window_manager = WindowsWindowManager()
        self._update_manager = WindowsUpdateManager()
        self._system_integration = WindowsSystemIntegration()
    
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