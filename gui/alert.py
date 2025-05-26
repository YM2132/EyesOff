import platform
import time
import subprocess
import os
from typing import Tuple, Optional, Callable

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
							 QGraphicsOpacityEffect, QDesktopWidget, QApplication,
							 QSystemTrayIcon)

# Try to import QtMultimedia for sound support
try:
    from PyQt5.QtMultimedia import QSound
    SOUND_SUPPORT = True
except ImportError:
    SOUND_SUPPORT = False

# Try to import notification library for macOS
if platform.system() == 'Darwin':
    try:
        # Check for native notification support via PyObjC
        import Foundation
        import UserNotifications

        from UserNotifications import (
            UNUserNotificationCenter,
            UNAuthorizationOptionAlert,
            UNAuthorizationOptionSound
        )

        NATIVE_NOTIFICATION_SUPPORT = True

    except ImportError:
        try:
            # Fall back to AppleScript if PyObjC is not available
            import subprocess
            NATIVE_NOTIFICATION_SUPPORT = True
            print("Native notifications using PyObjC not available, falling back to AppleScript")
        except ImportError:
            NATIVE_NOTIFICATION_SUPPORT = False
else:
    NATIVE_NOTIFICATION_SUPPORT = False

if platform.system() == 'Darwin':
    try:
        import objc
        from Cocoa import NSApp, NSRunningApplication, NSWorkspace, NSURL
        from AppKit import NSApplicationActivateAllWindows
        PYOBJC_AVAILABLE = True
    except ImportError:
        PYOBJC_AVAILABLE = False
        print("PyObjC not available - falling back to AppleScript method")

class AlertDialogSignals(QObject):
    """Signals for alert dialog"""
    # Signal emitted when an alert should be dismissed
    user_dismiss_alert = pyqtSignal()

class AlertDialog(QDialog):
    """
    Custom dialog for displaying privacy alerts.
    Supports animations, custom styles, and auto-dismissal.
    """
    # TODO: Add alert_on to this class
    def __init__(self, 
                parent=None,
                alert_on: bool = False,
                alert_text: str = "EYES OFF!!!",
                alert_color: Tuple[int, int, int] = (0, 0, 255),
                alert_opacity: float = 0.8,
                alert_size: Tuple[int, int] = (600, 300),
                alert_position: str = "center",
                enable_animations: bool = True,
                alert_duration: Optional[float] = None,
                alert_sound_enabled: bool = False,
                alert_sound_file: str = "",
                fullscreen_mode: bool = False,
                on_notification_clicked: Optional[Callable] = None, # TODO we should add a callback which opens the app?
                launch_app_enabled: bool = False,
                launch_app_path: str = "",):
        """
        Initialize the alert dialog.
        
        Args:
            parent: Parent widget
            alert_text: Text to display in the alert
            alert_color: Background color in BGR format (B, G, R)
            alert_opacity: Alert opacity (0.0-1.0)
            alert_size: Alert window size (width, height)
            alert_position: Alert position ('center', 'top', 'bottom')
            enable_animations: Whether to enable fade in/out animations
            alert_duration: Optional duration in seconds for the alert (None for manual dismiss)
            alert_sound_enabled: Whether to play a sound when the alert appears
            alert_sound_file: Path to the sound file
            fullscreen_mode: Whether to display in fullscreen mode
            use_native_notifications: Whether to use native OS notifications instead of dialog
            on_notification_clicked: Callback when notification is clicked
        """
        super().__init__(parent)

        # Signals
        self.signals = AlertDialogSignals()

        # Store settings
        self.alert_on = alert_on
        self.alert_text = alert_text
        self.alert_color = alert_color
        self.alert_opacity = alert_opacity
        self.alert_size = alert_size
        self.alert_position = alert_position
        self.enable_animations = enable_animations
        self.alert_duration = alert_duration
        self.alert_sound_enabled = alert_sound_enabled
        self.alert_sound_file = alert_sound_file
        self.fullscreen_mode = fullscreen_mode
        self.on_notification_clicked = on_notification_clicked
        self.launch_app_enabled = launch_app_enabled
        self.launch_app_path = launch_app_path
        
        # State variables
        self.dismiss_timer = None
        self.fade_animation = None
        self.sound = None
        self.tray_icon = None
        
        # Always initialize UI since we're using the hybrid approach
        self._init_ui()
        
        # Set up sound if enabled
        if self.alert_sound_enabled and SOUND_SUPPORT and self.alert_sound_file:
            try:
                self.sound = QSound(self.alert_sound_file)
            except Exception as e:
                print(f"Error loading sound: {e}")
    
        # Initialize system tray icon for notifications if parent available
        if parent is not None:
            self._init_tray_icon()

        # Request notification permissions if on macOS
        if platform.system() == 'Darwin' and NATIVE_NOTIFICATION_SUPPORT:
            self.request_notification_permissions()

    def _init_ui(self):
        """Initialize the UI components."""
        # Set up window properties
        self.setWindowTitle("Privacy Alert")

        # Use platform-specific window flags
        is_macos = platform.system() == 'Darwin'

        if self.fullscreen_mode:
            # For fullscreen, use more aggressive flags
            flags = Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint

            if is_macos:
                # macOS specific flags for maximum visibility across spaces
                flags |= Qt.Tool  # Hide from dock
            else:
                # For other platforms
                flags |= Qt.Tool | Qt.X11BypassWindowManagerHint

            self.setWindowFlags(flags)
            # Will be resized to full screen in showEvent
        else:
            # Standard popup flags
            flags = Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint

            if is_macos:
                # macOS specific flags
                flags |= Qt.Tool  # Hide from dock
            else:
                flags |= Qt.Tool

            self.setWindowFlags(flags)
            # Set window size
            self.resize(*self.alert_size)

        # Set background color (convert BGR to RGB for Qt)
        r, g, b = self.alert_color[2], self.alert_color[1], self.alert_color[0]
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(r, g, b))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Set up layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Add main alert text
        self.title_label = QLabel(self.alert_text)
        self.title_label.setFont(QFont("Arial", 36, QFont.Bold))  # Increased font size
        self.title_label.setStyleSheet("color: white;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Add description text
        desc_label = QLabel("Someone else is looking at your screen!")
        desc_label.setFont(QFont("Arial", 24))  # Increased font size
        desc_label.setStyleSheet("color: white;")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        # Add dismiss button
        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.setFont(QFont("Arial", 18))  # Increased font size
        #self.dismiss_button.clicked.connect(self.close)
        self.dismiss_button.clicked.connect(self._on_user_dismiss)
        # Make the button more prominent
        self.dismiss_button.setMinimumSize(150, 50)
        self.dismiss_button.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.8); color: black; border-radius: 10px;")
        layout.addWidget(self.dismiss_button, 0, Qt.AlignCenter)

        # Set layout
        self.setLayout(layout)

        # Apply opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(self.alert_opacity)
        self.setGraphicsEffect(self.opacity_effect)

        # Position the window
        self._position_window()
    
    def _position_window(self):
        """Position the window based on settings."""
        # Get the geometry of the active screen
        active_window = QApplication.activeWindow()
        
        if active_window:
            # Get screen that contains the active window
            screen_num = QApplication.desktop().screenNumber(active_window)
            desktop = QDesktopWidget().availableGeometry(screen_num)
        else:
            # Fall back to primary screen if no active window
            desktop = QDesktopWidget().availableGeometry()
        
        window_size = self.size()
        
        if self.alert_position == "top":
            x = desktop.x() + (desktop.width() - window_size.width()) // 2
            y = desktop.top() + 50
        elif self.alert_position == "bottom":
            x = desktop.x() + (desktop.width() - window_size.width()) // 2
            y = desktop.bottom() - window_size.height() - 50
        else:  # center
            x = desktop.x() + (desktop.width() - window_size.width()) // 2
            y = desktop.y() + (desktop.height() - window_size.height()) // 2
        
        self.move(x, y)
    
    def _fade_in(self):
        """Animate the alert fading in."""
        if self.fade_animation:
            self.fade_animation.stop()
            
        self.opacity_effect.setOpacity(0.0)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(self.alert_opacity)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_animation.start()
    
    def _fade_out(self):
        """Animate the alert fading out."""
        if self.fade_animation:
            self.fade_animation.stop()
            
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(self.opacity_effect.opacity())
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()
    
    def _setup_auto_dismiss(self):
        """Set up auto-dismissal timer if duration is specified."""
        if self.alert_duration is not None:
            self.dismiss_timer = QTimer(self)
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self._on_auto_dismiss)
            self.dismiss_timer.start(int(self.alert_duration * 1000))
    
    def _play_sound(self):
        """Play the alert sound if enabled."""
        if self.alert_sound_enabled and self.sound:
            self.sound.play()
    
    def _on_auto_dismiss(self):
        """Handle auto-dismiss timeout."""
        if self.enable_animations:
            self._fade_out()
        else:
            self.close()

    def _on_user_dismiss(self):
        """Handle user clicking the dismiss button"""
        self.signals.user_dismiss_alert.emit()

    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)

        # If fullscreen mode, resize to cover the entire screen
        if self.fullscreen_mode:
            # Get the geometry of the active screen
            desktop = QDesktopWidget()
            screen = desktop.screenNumber(QApplication.activeWindow() or self)
            screen_geom = desktop.screenGeometry(screen)

            # Cover the entire screen
            self.setGeometry(screen_geom)

            # Force window to be active but not minimized
            self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        else:
            # Position the window based on settings
            self._position_window()

        # Apply animations if enabled - make sure we have an opacity effect
        if not hasattr(self, 'opacity_effect') or self.opacity_effect is None:
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.opacity_effect.setOpacity(self.alert_opacity)
            self.setGraphicsEffect(self.opacity_effect)

        if self.enable_animations:
            self._fade_in()

        # Set up auto-dismiss if specified
        self._setup_auto_dismiss()

        # Play sound if enabled
        self._play_sound()

        # Set up timer to periodically raise window and keep it on the active space
        # Do this for all platforms, not just macOS
        self.raise_()
        self.activateWindow()

        # Create timer to periodically raise the window (important for keeping on top)
        if not hasattr(self, 'raise_timer') or not self.raise_timer.isActive():
            self.raise_timer = QTimer(self)
            self.raise_timer.timeout.connect(self._ensure_visibility)
            self.raise_timer.start(100)  # Check more frequently (every 100ms)

        # Launch external app if configured
        if self.launch_app_enabled and self.launch_app_path:
            print("TRYING TO LAUNCH APP")
            QTimer.singleShot(200, self._launch_external_app)  # Slight delay for better UX

    def _ensure_visibility(self):
        """Ensure the alert window remains visible across spaces in macOS."""
        # More aggressively raise the window and activate it
        self.raise_()
        self.activateWindow()

        # Force window to be active but not minimized
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)

        # On macOS, also reposition to active screen if needed
        if platform.system() == 'Darwin' and QApplication.activeWindow():
            # Get current active screen
            screen = QApplication.desktop().screenNumber(QApplication.activeWindow())
            current_screen_geom = QDesktopWidget().screenGeometry(screen)

            # If fullscreen mode, cover entire active screen
            if self.fullscreen_mode:
                if self.geometry() != current_screen_geom:
                    self.setGeometry(current_screen_geom)
            # Otherwise just make sure it's positioned properly on active screen
            else:
                window_size = self.size()
                if self.alert_position == "top":
                    x = current_screen_geom.x() + (current_screen_geom.width() - window_size.width()) // 2
                    y = current_screen_geom.y() + 50
                elif self.alert_position == "bottom":
                    x = current_screen_geom.x() + (current_screen_geom.width() - window_size.width()) // 2
                    y = current_screen_geom.y() + current_screen_geom.height() - window_size.height() - 50
                else:  # center
                    x = current_screen_geom.x() + (current_screen_geom.width() - window_size.width()) // 2
                    y = current_screen_geom.y() + (current_screen_geom.height() - window_size.height()) // 2

                self.move(x, y)
    
    def closeEvent(self, event):
        # already fading? let Qt close the window for real
        if getattr(self, "_is_fading", False):
            self._is_fading = False            # reset guard
            if hasattr(self, "raise_timer") and self.raise_timer.isActive():
                self.raise_timer.stop()
            super().closeEvent(event)
            return

        # start a single fade-out, then really close
        if self.enable_animations:
            self._is_fading = True
            self._fade_out()
            self.fade_animation.finished.connect(self.close)   # will run branch above
            event.ignore()
            return

        super().closeEvent(event)
    
    def _init_tray_icon(self):
        """Initialize system tray icon for notifications."""
        self.tray_icon = QSystemTrayIcon(self.parent())

        # TODO Add my icon to tray icon
        # Use your custom icon
        icon_path = 'path/to/your/eyesoff_refined_logo.png'
        self.tray_icon.setIcon(QIcon(icon_path))

        #self.tray_icon.setIcon(QIcon.fromTheme("dialog-warning"))  # Use a default icon
        
        # Connect the activated signal to handle notification click
        if self.on_notification_clicked:
            self.tray_icon.activated.connect(
                lambda reason: self.on_notification_clicked() 
                if reason == QSystemTrayIcon.Trigger else None
            )

    def request_notification_permissions(self):
        """Request permission to display notifications on macOS"""
    if platform.system() == 'Darwin' and NATIVE_NOTIFICATION_SUPPORT:
        try:
            # Define options (alert, sound)
            options = UNAuthorizationOptionAlert | UNAuthorizationOptionSound

            # Request authorization
            center = UNUserNotificationCenter.currentNotificationCenter()
            center.requestAuthorizationWithOptions_completionHandler_(
                options,
                lambda granted, error: print(f"Notification permission granted: {granted}")
            )
        except Exception as e:
            print(f"Error requesting notification permissions: {e}")

    def _show_macos_notification(self, title, subtitle, body, sound_name=None):
        """
        Show a native macOS notification using the UserNotifications framework
        """
        if platform.system() != 'Darwin' or not NATIVE_NOTIFICATION_SUPPORT:
            return

        try:
            from Foundation import NSDate
            from UserNotifications import (
                UNUserNotificationCenter,
                UNMutableNotificationContent,
                UNNotificationRequest,
                UNTimeIntervalNotificationTrigger,
                UNNotificationSound
            )

            # Get the notification center
            center = UNUserNotificationCenter.currentNotificationCenter()

            # Create notification content
            content = UNMutableNotificationContent.alloc().init()
            content.setTitle_(title)
            content.setSubtitle_(subtitle)
            content.setBody_(body)

            # Set sound if provided
            if sound_name:
                content.setSound_(UNNotificationSound.soundNamed_(sound_name))

            # Create a unique identifier for this notification
            request_id = f"privacy-alert-{NSDate.date().timeIntervalSince1970()}"

            # Create trigger (deliver immediately)
            trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(0.1, False)

            # Create request
            request = UNNotificationRequest.requestWithIdentifier_content_trigger_(
                request_id, content, trigger
            )

            # Add to notification center
            center.addNotificationRequest_withCompletionHandler_(request, None)
        except Exception as e:
            print(f"Error showing native macOS notification: {e}")
            # Fall back to AppleScript if PyObjC fails
            self._show_applescript_notification(title, body, sound_name)

    def _show_applescript_notification(self, title, body, sound_name=None):
        """Fall back to AppleScript for notifications if PyObjC fails"""
        try:
            import subprocess
            sound_part = f' sound name "{sound_name}"' if sound_name else ""
            applescript = f'''
            display notification "{body}" with title "{title}"{sound_part}
            '''
            subprocess.run(["osascript", "-e", applescript], check=True)
        except Exception as e:
            print(f"Error showing AppleScript notification: {e}")

    def _show_native_notification(self):
        ''' Show a native system notification. '''
        # Always allow showing notifications in hybrid mode
        
        # Make sure we don't show the popup when showing a notification
        # This prevents both popup and notification from appearing together
        if self.isVisible():
            self.close()
            
        # Play sound if enabled
        if self.alert_sound_enabled and SOUND_SUPPORT and self.sound:
            self.sound.play()
            
        # Use system tray notifications (works on most platforms)
        if self.tray_icon:
            self.tray_icon.show()
            self.tray_icon.showMessage(
                "Privacy Alert", 
                "Someone is looking at your screen! Check your privacy.",
                QSystemTrayIcon.Critical, 
                500  # Show for 0.5 seconds
            )

        # For macOS, use the native notification API
        if platform.system() == 'Darwin' and NATIVE_NOTIFICATION_SUPPORT:
            try:
                self._show_macos_notification(
                    title="EyesOff",
                    subtitle="Privacy Alert",
                    body="Someone is looking at your screen!",
                    sound_name="Sosumi"
                )
            except Exception as e:
                print(f"Error showing macOS notification: {e}")
        
        """# For macOS, we can also try using the native notification system via applescript
        # TODO - Switch to Mac native notification API to get greater control or a python lib to show mac notifications
        if platform.system() == 'Darwin' and NATIVE_NOTIFICATION_SUPPORT:
            try:
                # Create a more concise AppleScript command
                applescript = f'''
                display notification "Privacy Alert: Someone is looking at your screen." with title "EyesOff" sound name "Sosumi"
                '''
                subprocess.run(["osascript", "-e", applescript], check=True)
            except Exception as e:
                print(f"Error showing macOS notification: {e}")"""
                
        # Set up auto-dismiss for any resources
        if self.alert_duration is not None:
            self.dismiss_timer = QTimer(self)
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self.close)
            self.dismiss_timer.start(int(self.alert_duration * 1000))

    # TODO: behaviour if an app is already open?
    def _launch_external_app(self):
        """Launch and switch to the configured external app."""
        if not self.launch_app_enabled or not self.launch_app_path:
            return False

        try:
            print(f"Attempting to launch app: {self.launch_app_path}")

            if platform.system() == 'Darwin':
                return self._launch_macos_app()
            elif platform.system() == 'Windows':
                # Windows - use start command
                os.startfile(self.launch_app_path)
                return True
            else:
                # Linux - use xdg-open
                subprocess.Popen(['xdg-open', self.launch_app_path])
                return True
        except Exception as e:
            print(f"Error launching app: {e}")
            return False

    def _launch_macos_app(self):
        """Launch and activate app on macOS using the appropriate method."""
        try:
            # Get bundle identifier from the app bundle
            bundle_id = self._get_bundle_identifier(self.launch_app_path)

            if PYOBJC_AVAILABLE and bundle_id:
                # Use modern API for macOS 14+
                return self._launch_with_yield_activation(bundle_id)
            else:
                # Fallback to AppleScript method
                return self._launch_with_applescript()
        except Exception as e:
            print(f"Error in macOS launch: {e}")
            # Try fallback method if primary fails
            return self._launch_with_applescript()

    def _get_bundle_identifier(self, app_path):
        """Extract bundle identifier from .app bundle."""
        try:
            plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
            if os.path.exists(plist_path):
                # Use plutil to read the bundle identifier
                result = subprocess.run(
                    ['plutil', '-extract', 'CFBundleIdentifier', 'raw', plist_path],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception as e:
            print(f"Could not extract bundle identifier: {e}")
        return None

    def _launch_with_yield_activation(self, bundle_id):
        """Launch app using modern macOS 14+ cooperative activation."""
        try:
            # First yield activation to the target app
            # This tells macOS we're willing to give up focus
            if hasattr(NSApp, 'yieldActivationToApplicationWithBundleIdentifier_'):
                NSApp.yieldActivationToApplicationWithBundleIdentifier_(bundle_id)
                print(f"Yielded activation to bundle: {bundle_id}")

            # Get the shared workspace
            workspace = NSWorkspace.sharedWorkspace()

            # Check if app is already running by iterating through running applications
            running_app = None
            for app in workspace.runningApplications():
                if app.bundleIdentifier() == bundle_id:
                    running_app = app
                    break

            if running_app:
                # App is already running, use aggressive activation
                print(f"App already running, activating...")
                return self._activate_running_app(running_app, bundle_id)

            # App not running, launch it
            print(f"App not running, launching...")

            # Create NSURL for the app path
            app_url = NSURL.fileURLWithPath_(self.launch_app_path)

            # Launch the app and get the NSRunningApplication instance
            launched_app = workspace.launchApplicationAtURL_options_configuration_error_(
                app_url,
                NSApplicationActivateAllWindows,  # Launch and activate
                {},  # Empty configuration dictionary
                None  # Error pointer (we'll ignore errors)
            )

            if launched_app and launched_app[0]:
                print(f"Successfully launched: {launched_app}")
                # Give it a moment to fully launch, then activate
                QTimer.singleShot(300, lambda: self._activate_running_app(launched_app[0], bundle_id))
                return True
            else:
                # Fallback to subprocess if NSWorkspace fails
                print("NSWorkspace launch failed, using subprocess...")
                subprocess.Popen(['open', self.launch_app_path])

                # After launching, try to activate it after a short delay
                QTimer.singleShot(500, lambda: self._try_activate_by_bundle_id(bundle_id))
                return True

        except Exception as e:
            print(f"Error in yield activation method: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _activate_running_app(self, running_app, bundle_id):
        """Aggressively activate an already-running app using dock clicks."""
        try:
            app_name = os.path.basename(self.launch_app_path).replace('.app', '')

            # First, yield activation if available
            if hasattr(NSApp, 'yieldActivationToApplication_'):
                NSApp.yieldActivationToApplication_(running_app)
                print("Yielded activation to running app instance")

            # Try standard activation first
            success = running_app.activateWithOptions_(NSApplicationActivateAllWindows)
            print(f"Standard activation: {success}")

            # Always use dock double-click for running apps
            print(f"Using dock double-click for {app_name}")
            return self._activate_via_dock_double_click(app_name)

        except Exception as e:
            print(f"Error in activate running app: {e}")
            return False

    def _activate_via_dock_double_click(self, app_name):
        """Simulate double-clicking the app in the dock."""
        try:
            # AppleScript to double-click the dock icon
            applescript = f'''
            tell application "System Events"
                tell process "Dock"
                    set dockItems to UI elements of list 1

                    repeat with dockItem in dockItems
                        if name of dockItem contains "{app_name}" or description of dockItem contains "{app_name}" then
                            -- First click
                            click dockItem
                            delay 0.2
                            -- Second click
                            click dockItem
                            return true
                        end if
                    end repeat
                end tell
            end tell

            -- If dock click failed, try alternative method
            tell application "{app_name}"
                activate
                try
                    reopen  -- This simulates dock click behavior
                end try
            end tell
            '''

            result = subprocess.run(["osascript", "-e", applescript],
                                    capture_output=True, text=True)

            if result.returncode == 0:
                print(f"Dock double-click successful for {app_name}")
                return True
            else:
                print(f"Dock double-click error: {result.stderr}")
                # Fallback to simpler method
                return self._fallback_dock_click(app_name)

        except Exception as e:
            print(f"Error in dock double-click: {e}")
            return False

    def _fallback_dock_click(self, app_name):
        """Fallback method using perform action."""
        try:
            # Simpler approach that might work better on some systems
            applescript = f'''
            tell application "System Events"
                tell process "Dock"
                    -- Find and click the dock item
                    try
                        click UI element "{app_name}" of list 1
                        delay 0.1
                        click UI element "{app_name}" of list 1
                    on error
                        -- Try with different matching
                        set dockList to list 1
                        repeat with i from 1 to count of UI elements of dockList
                            set dockItem to UI element i of dockList
                            try
                                if name of dockItem contains "{app_name}" then
                                    click dockItem
                                    delay 0.1
                                    click dockItem
                                    exit repeat
                                end if
                            end try
                        end repeat
                    end try
                end tell
            end tell
            '''

            subprocess.run(["osascript", "-e", applescript], capture_output=True)
            print(f"Fallback dock click attempted for {app_name}")
            return True

        except Exception as e:
            print(f"Error in fallback dock click: {e}")
            return False

    def _try_activate_by_bundle_id(self, bundle_id):
        """Try to activate an app by bundle ID after it has launched."""
        try:
            workspace = NSWorkspace.sharedWorkspace()

            # Find the app in running applications
            for app in workspace.runningApplications():
                if app.bundleIdentifier() == bundle_id:
                    print(f"Found app: {bundle_id}")
                    # Use the aggressive activation method
                    self._activate_running_app(app, bundle_id)
                    break
        except Exception as e:
            print(f"Error in delayed activation: {e}")

    def _launch_with_applescript(self):
        """Fallback method using AppleScript."""
        try:
            # Extract app name for AppleScript
            app_name = os.path.basename(self.launch_app_path)
            app_name = app_name.replace('.app', '')

            # Launch the app first
            subprocess.Popen(['open', self.launch_app_path])

            # Schedule activation after a delay
            QTimer.singleShot(500, lambda: self._activate_macos_app(app_name))
            return True
        except Exception as e:
            print(f"Error in AppleScript method: {e}")
            return False

    def _activate_macos_app(self, app_name):
        """
        Bring the launched application to the foreground on macOS.
        This is the fallback method for older macOS versions.
        """
        try:
            # Enhanced AppleScript that tries multiple approaches
            applescript = f'''
            -- First try to activate by name
            try
                tell application "{app_name}" to activate
            on error
                -- If that fails, try using System Events
                tell application "System Events"
                    try
                        -- Find process by name
                        set frontProcess to first process whose name is "{app_name}"
                        set frontmost of frontProcess to true
                    on error
                        -- Last resort: try with .app extension
                        try
                            tell application "{app_name}.app" to activate
                        end try
                    end try
                end tell
            end try
            '''
            subprocess.run(["osascript", "-e", applescript], check=True)
            print(f"Activated app via AppleScript: {app_name}")
        except Exception as e:
            print(f"Error activating app: {e}")

    # TODO - Only shows system notification
    @pyqtSlot()
    def test_alert(self):
        """Show a test alert."""
        # For hybrid approach, always show the dialog
        # If already visible, just reset timers/animations
        if self.isVisible():
            # Reset auto-dismiss timer if active
            if self.dismiss_timer and self.dismiss_timer.isActive():
                self.dismiss_timer.stop()
                self._setup_auto_dismiss()
        else:
            self.show()
            
        # Also show a notification for testing
        self._show_native_notification()
    
    def update_settings(self,
                       alert_on: Optional[bool] = None,
                       alert_text: Optional[str] = None,
                       alert_color: Optional[Tuple[int, int, int]] = None,
                       alert_opacity: Optional[float] = None,
                       alert_size: Optional[Tuple[int, int]] = None,
                       alert_position: Optional[str] = None,
                       enable_animations: Optional[bool] = None,
                       alert_duration: Optional[float] = None,
                       alert_sound_enabled: Optional[bool] = None,
                       alert_sound_file: Optional[str] = None,
                       fullscreen_mode: Optional[bool] = None,
                       on_notification_clicked: Optional[Callable] = None,
                       launch_app_enabled: Optional[bool] = None,
                       launch_app_path: Optional[str] = None):
        """
        Update alert settings.
        
        Args:
            alert_on: Is alert selected?
            alert_text: New alert text
            alert_color: New background color
            alert_opacity: New opacity
            alert_size: New window size
            alert_position: New window position
            enable_animations: Whether to enable animations
            alert_duration: Auto-dismiss duration
            alert_sound_enabled: Whether to enable sound
            alert_sound_file: Path to sound file
            fullscreen_mode: Whether to show alert in fullscreen mode
            use_native_notifications: Whether to use native OS notifications
            on_notification_clicked: Callback when notification is clicked
        """
        # Handle alert_on mode change
        if alert_on is not None and alert_on != self.alert_on:
            self.alert_on = alert_on

            # If turning alerts off and the dialog is visible, close it
            if not alert_on and self.isVisible():
                self.close()

            # Make sure UI is initialized if needed (similar to previous logic)
            if not hasattr(self, 'title_label'):
                self._init_ui()

            # Make sure tray icon is initialized for notifications
            if not self.tray_icon and self.parent() is not None:
                self._init_tray_icon()

            # Also update the config manager if available
            if self.parent() and hasattr(self.parent(), 'config_manager'):
                self.parent().config_manager.set("alert_on", alert_on)
                
        # Update callback if provided
        if on_notification_clicked is not None:
            self.on_notification_clicked = on_notification_clicked
            # Update tray icon signal if it exists
            if self.tray_icon and self.on_notification_clicked:
                try:
                    self.tray_icon.activated.disconnect()  # Disconnect any existing connections
                except:
                    pass
                self.tray_icon.activated.connect(
                    lambda reason: self.on_notification_clicked() 
                    if reason == QSystemTrayIcon.Trigger else None
                )

        # Update app launch settings
        if launch_app_enabled is not None:
            self.launch_app_enabled = launch_app_enabled
        if launch_app_path is not None:
            self.launch_app_path = launch_app_path

        # Store alert_on setting if provided - alert_on isnt directly used in "alert.py" it is handled in main_window
        if alert_on is not None:
            self.alert_on = alert_on  # Properly store the value
            # Also update the config manager if available
            if self.parent() and hasattr(self.parent(), 'config_manager'):
                self.parent().config_manager.set("alert_on", alert_on)
        
        # Other settings that apply to both dialog and notification modes
        if alert_text is not None:
            self.alert_text = alert_text
            if hasattr(self, 'title_label'):
                self.title_label.setText(alert_text)

        if alert_color is not None:
            self.alert_color = alert_color
            # Apply color change immediately for visual update
            r, g, b = self.alert_color[2], self.alert_color[1], self.alert_color[0]
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor(r, g, b))
            self.setPalette(palette)
            self.setAutoFillBackground(True)
            if self.isVisible():
                self.update()  # Force a repaint

        if alert_opacity is not None:
            self.alert_opacity = alert_opacity
            if hasattr(self, 'opacity_effect'):
                self.opacity_effect.setOpacity(alert_opacity)
                if self.isVisible():
                    self.update()  # Force a repaint

        if alert_size is not None:
            self.alert_size = alert_size
            if not self.fullscreen_mode:  # Only resize if not in fullscreen
                self.resize(*self.alert_size)
                self._position_window()

        if alert_position is not None:
            self.alert_position = alert_position
            if not self.fullscreen_mode:  # Only reposition if not in fullscreen #TODO: If in fullscreen we should disable the alert_position settings
                self._position_window()

                # If fullscreen mode changed, we need to recreate the window with new flags
                if fullscreen_mode is not None and fullscreen_mode != self.fullscreen_mode:
                    # Update the state variable FIRST before recreating UI
                    self.fullscreen_mode = fullscreen_mode
                    print(f"DEBUG: Updating fullscreen mode to {self.fullscreen_mode}")

                    # Close and reopen to apply the new window flags
                    if self.isVisible():
                        visible = True
                        self.close()
                        # Recreate UI with new settings
                        self._init_ui()
                        if visible:
                            self.show()
                    else:
                        # Just recreate UI with new settings
                        self._init_ui()

        if alert_duration is not None:
            self.alert_duration = alert_duration
            
        if alert_sound_enabled is not None:
            self.alert_sound_enabled = alert_sound_enabled
            
        if alert_sound_file is not None and alert_sound_file != self.alert_sound_file:
            self.alert_sound_file = alert_sound_file
            if SOUND_SUPPORT and self.alert_sound_file:
                try:
                    self.sound = QSound(self.alert_sound_file)
                except Exception as e:
                    print(f"Error loading sound: {e}")
                    self.sound = None
