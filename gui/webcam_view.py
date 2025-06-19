import os
import time
import math
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QRect, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QBrush, QFont, QColor, QPainterPath
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSizePolicy, QGraphicsDropShadowEffect

from utils.display import cv_to_pixmap, apply_privacy_blur, apply_pixelation


class WebcamView(QWidget):
    """
    Widget for displaying the webcam feed with detection visualization.
    """
    
    # Signal emitted when monitoring is toggled
    monitoring_toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        """Initialize the webcam view widget."""
        super().__init__(parent)
        
        # State variables
        self.last_frame = None
        self.current_frame = None
        self.detection_result = None
        self.num_faces = 0
        self.num_looking = 0
        self.bboxes = []
        self.face_threshold = 1
        self.alert_active = False
        self.privacy_mode = False
        self.is_monitoring = True
        self.scaled_pixmap = None
        
        # Initialize UI
        self._init_ui()

        # Dir to save snapshots
        self.dir_to_save = None

    def _init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout()

        # Container for the webcam display
        webcam_container = QWidget()
        webcam_container.setStyleSheet("background-color: black;")
        webcam_container_layout = QVBoxLayout(webcam_container)

        # Webcam display label with modern styling
        self.webcam_label = QLabel()
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.webcam_label.setScaledContents(False)  # We'll handle scaling manually for quality
        
        # Add modern styling with rounded corners and subtle shadow
        self.webcam_label.setStyleSheet("""
            QLabel {
                border-radius: 18px;
                background-color: black;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        
        # Add subtle drop shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.webcam_label.setGraphicsEffect(shadow)

        # Add "No Camera" text initially
        initial_pixmap = QPixmap(640, 480)
        initial_pixmap.fill(Qt.black)
        self.webcam_label.setPixmap(initial_pixmap)

        # Add webcam label to container with centering
        webcam_container_layout.addWidget(self.webcam_label, 0, Qt.AlignCenter)

        # Add container to main layout
        main_layout.addWidget(webcam_container, 1)  # Give it a stretch factor of 1

        # Controls layout - keep this separate from the video display
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 5, 10, 5)

        # Start/Stop button
        self.toggle_button = QPushButton("Start Monitoring")
        self.toggle_button.setToolTip("Start or stop the detector")
        self.toggle_button.clicked.connect(self._on_toggle_clicked)

        # Snapshot button
        self.snapshot_button = QPushButton("Snapshot")
        self.snapshot_button.setToolTip("Take a snapshot of the current view")
        self.snapshot_button.clicked.connect(self.on_snapshot_clicked)

        # Add controls to layout
        controls_layout.addWidget(self.toggle_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.snapshot_button)

        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)
    
    
    @pyqtSlot(np.ndarray)
    def update_frame(self, frame: np.ndarray):
        """
        Update the displayed frame.
        
        Args:
            frame: New frame to display
        """
        self.last_frame = self.current_frame
        self.current_frame = frame.copy()
        
        if self.detection_result is not None:
            self._update_display()
    
    @pyqtSlot(int, list, np.ndarray, int)
    def update_detection(self, num_faces: int, bboxes: List[Tuple[int, int, int, int]], annotated_frame: np.ndarray, num_looking: int):
        """
        Update detection results.
        
        Args:
            num_faces: Number of faces detected
            bboxes: Bounding boxes of detected faces
            annotated_frame: Frame with detection annotations
        """
        self.num_faces = num_faces
        self.bboxes = bboxes
        self.detection_result = annotated_frame.copy()
        self.num_looking = num_looking
        
        # Update display if we have a current frame
        if self.current_frame is not None:
            self._update_display()
    
    @pyqtSlot(bool)
    def update_alert_state(self, is_active: bool):
        """
        Update alert state.
        
        Args:
            is_active: Whether an alert is currently active
        """
        self.alert_active = is_active
        
        # Update display if we have current detection results
        if self.detection_result is not None:
            self._update_display()
    
    def update_settings(self, settings: Dict[str, Any]):
        """
        Update display settings.
        
        Args:
            settings: New settings
        """
        if 'face_threshold' in settings:
            self.face_threshold = settings['face_threshold']
        
        if 'privacy_mode' in settings:
            self.privacy_mode = settings['privacy_mode']
        
        # Update display if we have current detection results
        if self.detection_result is not None:
            self._update_display()

    def _update_display(self):
        """Update the display with current frame and detection results."""
        if self.current_frame is None:
            return

        # Start with the annotated frame from detection (includes bounding boxes)
        display_frame = self.detection_result.copy()

        # Apply privacy mode if enabled
        if self.privacy_mode and self.bboxes:
            display_frame = apply_pixelation(display_frame, self.bboxes)

        # Convert to QPixmap directly - let Qt handle all scaling
        pixmap = cv_to_pixmap(display_frame)

        # Scale the pixmap to fit the label while maintaining aspect ratio
        label_size = self.webcam_label.size()
        self.scaled_pixmap = pixmap.scaled(
            label_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation  # Always use smooth transformation for quality
        )

        # Create custom pixmap with overlays
        self._draw_overlays()
    
    def _draw_overlays(self):
        """Draw UI overlays using PyQt."""
        # Create a new pixmap to draw on
        final_pixmap = self.scaled_pixmap.copy()
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw info panel
        self._draw_info_panel(painter)
        
        painter.end()
        
        # Set the final pixmap
        self.webcam_label.setPixmap(final_pixmap)
    
    def _draw_info_panel(self, painter: QPainter):
        """Draw the info panel with detection information."""
        # Prepare background panel with modern styling
        panel_width = 280
        panel_height = 90
        panel_margin = 20
        panel_rect = QRect(panel_margin, panel_margin, panel_width, panel_height)
        
        # Create glass-morphism effect background
        # Draw backdrop blur effect background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 10)))  # Very subtle white
        painter.drawRoundedRect(panel_rect, 12, 12)
        
        # Draw main panel with gradient
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))  # Semi-transparent black
        painter.drawRoundedRect(panel_rect, 12, 12)
        
        # Face count text with color based on threshold
        face_color = QColor(255, 75, 75) if self.num_faces > self.face_threshold else QColor(75, 255, 75)
        font = QFont("Arial", 15, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(face_color))
        
        text_x = panel_margin + 15
        if self.num_faces == 1:
            painter.drawText(text_x, panel_margin + 35, f"{self.num_faces} face detected")
        else:
            painter.drawText(text_x, panel_margin + 35, f"{self.num_faces} faces detected")

        # Looking count with modern styling
        looking_font = QFont("Arial", 13)
        painter.setFont(looking_font)
        painter.setPen(QPen(QColor(255, 255, 255, 220)))  # Slightly transparent white
        
        if self.num_looking == 1:
            painter.drawText(text_x, panel_margin + 60, f"{self.num_looking} person is looking at your screen")
        else:
            painter.drawText(text_x, panel_margin + 60, f"{self.num_looking} people are looking at your screen")
        
        # Alert indicator with modern styling
        if self.alert_active:
            # Draw a modern alert badge in top right
            indicator_margin = 20
            indicator_size = 40
            indicator_x = self.scaled_pixmap.width() - indicator_margin - indicator_size
            indicator_y = indicator_margin
            
            # Create pulsing effect with time-based opacity
            pulse = abs(math.sin(time.time() * 3))  # 3Hz pulse
            base_opacity = 200
            pulse_opacity = int(base_opacity + (255 - base_opacity) * pulse)
            
            # Draw glow effect
            glow_rect = QRect(indicator_x - 4, indicator_y - 4, indicator_size + 8, indicator_size + 8)
            painter.setBrush(QBrush(QColor(255, 59, 48, pulse_opacity // 3)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(glow_rect, (indicator_size + 8) // 2, (indicator_size + 8) // 2)
            
            # Create rounded rectangle for alert badge
            alert_rect = QRect(indicator_x, indicator_y, indicator_size, indicator_size)
            painter.setBrush(QBrush(QColor(255, 59, 48, pulse_opacity)))  # iOS-style red with pulse
            painter.drawRoundedRect(alert_rect, indicator_size // 2, indicator_size // 2)
            
            # Draw exclamation mark
            painter.setPen(QPen(Qt.white, 3))
            painter.setFont(QFont("Arial", 22, QFont.Bold))
            painter.drawText(alert_rect, Qt.AlignCenter, "!")
    
    def set_privacy_mode(self, enabled: bool):
        """
        Set privacy mode programmatically.
        
        Args:
            enabled: Whether privacy mode is enabled
        """
        self.privacy_mode = enabled
        
        # Update display if we have current detection results
        if self.detection_result is not None:
            self._update_display()
    
    def _on_toggle_clicked(self):
        """Handle start/stop button click."""
        # Get button text to determine current state
        if self.toggle_button.text() == "Stop Monitoring":
            # Currently running, emit signal to stop
            self.monitoring_toggled.emit(False)
            self.toggle_button.setText("Start Monitoring")
        else:
            # Currently stopped, emit signal to start
            self.monitoring_toggled.emit(True)
            self.toggle_button.setText("Stop Monitoring")

    # TODO - Make this behaviour activate by default but add an option to turn it off
    def on_snapshot_clicked(self):
        """Handle snapshot button click."""
        if self.current_frame is not None:
            # Get timestamp for filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"eyesoff_snapshot_{timestamp}.jpg"

            # If the dir_to_save doesn't exist we should make it
            # TODO - This may require perms
            if not os.path.exists(os.path.expanduser(self.dir_to_save)):
                os.makedirs(os.path.expanduser(self.dir_to_save))

            path_to_save = os.path.expanduser(os.path.join(self.dir_to_save, filename))
            
            # Save current display frame
            if self.detection_result is not None:
                cv2.imwrite(path_to_save, self.detection_result)

                # TODO - Add a notification to tell the user the snapshot was saved
                print(f"Snapshot saved as {filename}")
    
    def set_monitoring_state(self, is_monitoring: bool):
        """
        Update the monitoring state and button.
        
        Args:
            is_monitoring: Whether monitoring is active
        """
        self.is_monitoring = is_monitoring
        button_text = "Stop Monitoring" if is_monitoring else "Start Monitoring"
        self.toggle_button.setText(button_text)
        
        # Enable or disable snapshot button based on monitoring state
        self.snapshot_button.setEnabled(is_monitoring)
        
    def clear_display(self):
        """Clear the display."""
        # Create a blank black frame
        blank = QPixmap(640, 480)
        blank.fill(Qt.black)
        self.webcam_label.setPixmap(blank)
        
        # Reset state
        self.alert_active = False
        self.current_frame = None
        self.detection_result = None
        self.num_faces = 0
        self.bboxes = []

    def resizeEvent(self, event):
        """Handle resize events to adjust the display."""
        super().resizeEvent(event)
        if hasattr(self, 'detection_result') and self.detection_result is not None:
            self._update_display()