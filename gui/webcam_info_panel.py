import time
import math
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect


class AlertIndicator(QWidget):
    """Pulsing alert indicator widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        
        # Animation properties
        self._scale = 1.0
        
        # Animation setup
        self.pulse_animation = QPropertyAnimation(self, b"scale")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(1.2)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_animation.setLoopCount(-1)  # Infinite
        
        # Auto-reverse the animation
        self.pulse_animation.finished.connect(self._reverse_animation)
        
    def _reverse_animation(self):
        """Reverse the animation direction."""
        start = self.pulse_animation.startValue()
        end = self.pulse_animation.endValue()
        self.pulse_animation.setStartValue(end)
        self.pulse_animation.setEndValue(start)
        self.pulse_animation.start()
    
    @pyqtProperty(float)
    def scale(self):
        """Scale property for animation."""
        return self._scale
    
    @scale.setter
    def scale(self, value):
        """Set scale and trigger repaint."""
        self._scale = value
        self.update()
    
    def start_pulsing(self):
        """Start the pulse animation."""
        self.pulse_animation.start()
        
    def stop_pulsing(self):
        """Stop the pulse animation."""
        self.pulse_animation.stop()
        self._scale = 1.0
        self.update()
        
    def paintEvent(self, event):
        """Draw the alert indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions based on scale
        center = self.rect().center()
        base_radius = 15
        scaled_radius = base_radius * self._scale
        
        # Add time-based pulsing for additional effect
        time_pulse = abs(math.sin(time.time() * 3))  # 3Hz pulse
        glow_radius = scaled_radius + 4 * time_pulse
        
        # Draw glow effect
        glow_gradient = QRadialGradient(center, glow_radius)
        glow_gradient.setColorAt(0, QColor(255, 59, 48, 60))
        glow_gradient.setColorAt(1, QColor(255, 59, 48, 0))
        
        painter.setBrush(glow_gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, int(glow_radius), int(glow_radius))
        
        # Draw main circle with gradient
        gradient = QRadialGradient(center, scaled_radius)
        gradient.setColorAt(0, QColor(255, 59, 48, 255))
        gradient.setColorAt(0.8, QColor(255, 59, 48, 230))
        gradient.setColorAt(1, QColor(255, 59, 48, 200))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, int(scaled_radius), int(scaled_radius))
        
        # Draw exclamation mark
        painter.setPen(QPen(Qt.white, 3))
        painter.setFont(QFont("Arial", int(16 * self._scale), QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "!")


class WebcamInfoPanel(QWidget):
    """A modern info panel widget for displaying detection statistics."""
    
    # Signals
    clicked = pyqtSignal()
    settings_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.num_faces = 0
        self.num_looking = 0
        self.face_threshold = 1
        self.alert_active = False
        
        # Dragging state
        self._drag_position = None
        
        # UI Setup
        self._init_ui()

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._apply_styling()
        
        # Position and size
        self.setFixedSize(280, 90)
        self.move(20, 20)  # Default position
        
    def _init_ui(self):
        """Initialize the UI components."""
        # Set window flags for overlay behavior
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main container with rounded corners
        self.container = QWidget(self)
        self.container.setObjectName("infoContainer")
        self.container.setGeometry(0, 0, 280, 90)
        
        # Layout
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Face count label
        self.face_count_label = QLabel("0 faces detected")
        self.face_count_label.setObjectName("faceCountLabel")
        
        # Looking count label
        self.looking_count_label = QLabel("0 people looking at your screen")
        self.looking_count_label.setObjectName("lookingCountLabel")
        
        layout.addWidget(self.face_count_label)
        layout.addWidget(self.looking_count_label)
        
        # Alert indicator (separate widget, not in container)
        self.alert_indicator = AlertIndicator(self.parent())  # Use parent's parent
        self.alert_indicator.hide()
        
        # Make interactive
        self.setCursor(Qt.PointingHandCursor)
        
    def _apply_styling(self):
        """Apply modern glass-morphism styling."""
        self.setStyleSheet("""
            #infoContainer {
                background-color: rgba(0, 0, 0, 160);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 10);
            }
            
            #faceCountLabel {
                color: white;
                font-family: Arial;
                font-size: 15px;
                font-weight: bold;
                padding: 2px;
            }
            
            #lookingCountLabel {
                color: rgba(255, 255, 255, 220);
                font-family: Arial;
                font-size: 13px;
                padding: 2px;
            }
        """)
        
        # Add drop shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
    def update_detection_info(self, num_faces, num_looking, face_threshold):
        """Update the displayed information."""
        self.num_faces = num_faces
        self.num_looking = num_looking
        self.face_threshold = face_threshold
        
        # Update face count with color
        face_color = "#FF4B4B" if num_faces > face_threshold else "#4BFF4B"
        face_text = f"{num_faces} face{'s' if num_faces != 1 else ''} detected"
        self.face_count_label.setText(face_text)
        self.face_count_label.setStyleSheet(f"""
            #faceCountLabel {{
                color: {face_color};
                font-family: Arial;
                font-size: 15px;
                font-weight: bold;
                padding: 2px;
            }}
        """)
        
        # Update looking count
        looking_text = f"{num_looking} {'person is' if num_looking == 1 else 'people are'} looking at your screen"
        self.looking_count_label.setText(looking_text)
        
    def set_alert_active(self, active):
        """Show/hide alert indicator."""
        self.alert_active = active
        if active and self.parent():
            # Position alert indicator in top-right of parent
            parent_rect = self.parent().rect()
            self.alert_indicator.move(
                parent_rect.width() - 60,
                20
            )
            self.alert_indicator.show()
            self.alert_indicator.start_pulsing()
        else:
            self.alert_indicator.hide()
            self.alert_indicator.stop_pulsing()
            
    def mousePressEvent(self, event):
        """Emit the clicked signal but do *not* start a drag."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()          # keep the click behaviour
            event.accept()               # swallow the event
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Ignore mouse moves so the widget never re-positions."""
        event.ignore()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._drag_position = None
            event.accept()
            
    def enterEvent(self, event):
        """Handle mouse enter for hover effects."""
        # Add subtle hover effect
        self.container.setStyleSheet("""
            #infoContainer {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 20);
            }
        """)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._apply_styling()  # Reset to normal style
        
    def contextMenuEvent(self, event):
        """Handle right-click for settings."""
        self.settings_requested.emit()
        event.accept()