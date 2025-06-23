import os
import time
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy

from utils.display import cv_to_pixmap, apply_pixelation
from gui.webcam_info_panel import WebcamInfoPanel


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
        
        # Create info panel widget
        self.info_panel = WebcamInfoPanel(self)
        self.info_panel.show()

    def _init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Webcam display label - NO EFFECTS, NO CONTAINER
        self.webcam_label = QLabel()
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.webcam_label.setScaledContents(False)
        self.webcam_label.setStyleSheet("background-color: black;")

        # Initial pixmap
        initial_pixmap = QPixmap(640, 480)
        initial_pixmap.fill(Qt.black)
        self.webcam_label.setPixmap(initial_pixmap)

        # Add webcam directly to layout
        main_layout.addWidget(self.webcam_label, 1)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 5, 10, 5)

        self.toggle_button = QPushButton("Start Monitoring")
        self.toggle_button.clicked.connect(self._on_toggle_clicked)

        self.snapshot_button = QPushButton("Snapshot")
        self.snapshot_button.clicked.connect(self.on_snapshot_clicked)

        controls_layout.addWidget(self.toggle_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.snapshot_button)

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
        self.info_panel.set_alert_active(is_active)

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
            Qt.FastTransformation  # Always use smooth transformation for quality
        )

        # Update info panel instead of drawing overlays
        self.info_panel.update_detection_info(
            self.num_faces, 
            self.num_looking, 
            self.face_threshold
        )
        
        # Set the pixmap directly without overlays
        self.webcam_label.setPixmap(self.scaled_pixmap)


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
        
        # Reposition alert indicator if it's active
        if hasattr(self, 'info_panel') and self.info_panel.alert_active:
            self.info_panel.set_alert_active(True)
            
        # Update display if we have detection results
        if hasattr(self, 'detection_result') and self.detection_result is not None:
            self._update_display()
