import platform
import time
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

class AlertDialogSignals(QObject):
    """Signals for alert dialog"""
    # Signal emitted when an alert should be dismissed
    user_dismiss_alert = pyqtSignal()

class AlertDialog(QDialog):
    """
    Custom dialog for displaying privacy alerts.
    Supports animations, custom styles, and auto-dismissal.
    """
    
    def __init__(self, 
                parent=None, 
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
                use_native_notifications: bool = False,
                on_notification_clicked: Optional[Callable] = None):
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
        self.use_native_notifications = use_native_notifications
        self.on_notification_clicked = on_notification_clicked
        
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
        """Handle dialog close event."""
        # Cancel dismiss timer if active
        if self.dismiss_timer and self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
        
        # Stop the raise timer if active
        if hasattr(self, 'raise_timer') and self.raise_timer.isActive():
            self.raise_timer.stop()
        
        # If animations are enabled and not already fading out
        if self.enable_animations and (not self.fade_animation or not self.fade_animation.state() == QPropertyAnimation.Running):
            self._fade_out()
            event.ignore()  # Ignore this close event, will be closed after animation
        else:
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
        """
        Request permission to display notifications on macOS
        """
        if platform.system() == 'Darwin' and NATIVE_NOTIFICATION_SUPPORT:
            try:
                from Foundation import NSDate
                from UserNotifications import (
                    UNUserNotificationCenter,
                    UNAuthorizationOptions
                )

                # Define options (alert, sound, badge)
                options = (
                        UNAuthorizationOptions.UNAuthorizationOptionAlert |
                        UNAuthorizationOptions.UNAuthorizationOptionSound
                )

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
                       use_native_notifications: Optional[bool] = None,
                       on_notification_clicked: Optional[Callable] = None):
        """
        Update alert settings.
        
        Args:
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
        # Handle notification mode change first
        notification_mode_changed = False
        if use_native_notifications is not None and use_native_notifications != self.use_native_notifications:
            self.use_native_notifications = use_native_notifications
            notification_mode_changed = True
            
            # If switching to native notifications, we may need to close the dialog
            if self.use_native_notifications and self.isVisible():
                self.close()
                
            # If switching from native notifications, we need to init UI
            if not self.use_native_notifications and not hasattr(self, 'title_label'):
                self._init_ui()
                
            # Initialize tray icon if needed
            if self.use_native_notifications and not self.tray_icon and self.parent() is not None:
                self._init_tray_icon()
                
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
        
        # Other settings that apply to both dialog and notification modes
        if alert_text is not None:
            self.alert_text = alert_text
            if hasattr(self, 'title_label'):
                self.title_label.setText(alert_text)
            
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
        
        # Settings only applicable to dialog mode
        if not self.use_native_notifications:
            if alert_color is not None:
                self.alert_color = alert_color
                r, g, b = self.alert_color[2], self.alert_color[1], self.alert_color[0]
                palette = self.palette()
                palette.setColor(QPalette.Window, QColor(r, g, b))
                self.setPalette(palette)
                
            if alert_opacity is not None:
                self.alert_opacity = alert_opacity
                self.opacity_effect.setOpacity(alert_opacity)
                
            if alert_size is not None:
                self.alert_size = alert_size
                if not self.fullscreen_mode:  # Only resize if not in fullscreen
                    self.resize(*self.alert_size)
                    self._position_window()
                
            if alert_position is not None:
                self.alert_position = alert_position
                if not self.fullscreen_mode:  # Only reposition if not in fullscreen
                    self._position_window()
                
            if enable_animations is not None:
                self.enable_animations = enable_animations
                    
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