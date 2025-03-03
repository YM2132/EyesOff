from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                           QGraphicsOpacityEffect, QDesktopWidget)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

import time
from typing import Tuple, Optional

# Try to import QtMultimedia for sound support
try:
    from PyQt5.QtMultimedia import QSound
    SOUND_SUPPORT = True
except ImportError:
    SOUND_SUPPORT = False


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
                alert_sound_file: str = ""):
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
        """
        super().__init__(parent)
        
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
        
        # State variables
        self.dismiss_timer = None
        self.fade_animation = None
        self.sound = None
        
        # Initialize UI
        self._init_ui()
        
        # Set up sound if enabled
        if self.alert_sound_enabled and SOUND_SUPPORT and self.alert_sound_file:
            try:
                self.sound = QSound(self.alert_sound_file)
            except Exception as e:
                print(f"Error loading sound: {e}")
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Set up window properties
        self.setWindowTitle("Privacy Alert")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint |
            Qt.Tool  # Hide from taskbar
        )
        
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
        
        # Add alert icon (placeholder - would use an actual icon in a real app)
        # icon_label = QLabel()
        # icon_label.setPixmap(QIcon.fromTheme("dialog-warning").pixmap(64, 64))
        # icon_label.setAlignment(Qt.AlignCenter)
        # layout.addWidget(icon_label)
        
        # Add main alert text
        self.title_label = QLabel(self.alert_text)
        self.title_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.title_label.setStyleSheet("color: white;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Add description text
        desc_label = QLabel("Someone else is looking at your screen!")
        desc_label.setFont(QFont("Arial", 12))
        desc_label.setStyleSheet("color: white;")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add dismiss button
        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.setFont(QFont("Arial", 10))
        self.dismiss_button.clicked.connect(self.close)
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
        desktop = QDesktopWidget().availableGeometry()
        window_size = self.size()
        
        if self.alert_position == "top":
            x = (desktop.width() - window_size.width()) // 2
            y = desktop.top() + 50
        elif self.alert_position == "bottom":
            x = (desktop.width() - window_size.width()) // 2
            y = desktop.bottom() - window_size.height() - 50
        else:  # center
            x = (desktop.width() - window_size.width()) // 2
            y = (desktop.height() - window_size.height()) // 2
        
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
    
    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        
        # Apply animations if enabled
        if self.enable_animations:
            self._fade_in()
        
        # Set up auto-dismiss if specified
        self._setup_auto_dismiss()
        
        # Play sound if enabled
        self._play_sound()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Cancel dismiss timer if active
        if self.dismiss_timer and self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
        
        # If animations are enabled and not already fading out
        if self.enable_animations and (not self.fade_animation or not self.fade_animation.state() == QPropertyAnimation.Running):
            self._fade_out()
            event.ignore()  # Ignore this close event, will be closed after animation
        else:
            super().closeEvent(event)
    
    @pyqtSlot()
    def test_alert(self):
        """Show a test alert."""
        # If already visible, just reset timers/animations
        if self.isVisible():
            # Reset auto-dismiss timer if active
            if self.dismiss_timer and self.dismiss_timer.isActive():
                self.dismiss_timer.stop()
                self._setup_auto_dismiss()
        else:
            self.show()
    
    def update_settings(self, 
                       alert_text: Optional[str] = None,
                       alert_color: Optional[Tuple[int, int, int]] = None,
                       alert_opacity: Optional[float] = None,
                       alert_size: Optional[Tuple[int, int]] = None,
                       alert_position: Optional[str] = None,
                       enable_animations: Optional[bool] = None,
                       alert_duration: Optional[float] = None,
                       alert_sound_enabled: Optional[bool] = None,
                       alert_sound_file: Optional[str] = None):
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
        """
        # Update only provided settings
        if alert_text is not None:
            self.alert_text = alert_text
            self.title_label.setText(alert_text)
            
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
            self.resize(*self.alert_size)
            self._position_window()
            
        if alert_position is not None:
            self.alert_position = alert_position
            self._position_window()
            
        if enable_animations is not None:
            self.enable_animations = enable_animations
            
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