from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage

import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Any, Optional

from utils.display import cv_to_pixmap, apply_privacy_blur, apply_pixelation, draw_detection_info


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
        self.bboxes = []
        self.fps = 0
        self.face_threshold = 1
        self.alert_active = False
        self.privacy_mode = False
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.is_monitoring = True
        
        # Initialize UI
        self._init_ui()
        
        # Set up FPS timer
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(1000)  # Update FPS every second

    def _init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout()

        # Container for the webcam display
        webcam_container = QWidget()
        webcam_container.setStyleSheet("background-color: black;")
        webcam_container_layout = QVBoxLayout(webcam_container)

        # Webcam display label
        self.webcam_label = QLabel()
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        self.snapshot_button.clicked.connect(self._on_snapshot_clicked)

        # Add controls to layout
        controls_layout.addWidget(self.toggle_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.snapshot_button)

        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)
    
    def _update_fps(self):
        """Update FPS calculation."""
        if self.frame_count > 0:
            current_time = time.time()
            elapsed = current_time - self.last_fps_time
            if elapsed > 0:
                self.fps = self.frame_count / elapsed
                self.frame_count = 0
                self.last_fps_time = current_time
    
    @pyqtSlot(np.ndarray)
    def update_frame(self, frame: np.ndarray):
        """
        Update the displayed frame.
        
        Args:
            frame: New frame to display
        """
        self.last_frame = self.current_frame
        self.current_frame = frame.copy()
        
        # Increment frame counter for FPS calculation
        self.frame_count += 1
        
        if self.detection_result is not None:
            self._update_display()
    
    @pyqtSlot(int, list, np.ndarray)
    def update_detection(self, num_faces: int, bboxes: List[Tuple[int, int, int, int]], annotated_frame: np.ndarray):
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

        # Start with the annotated frame from detection
        display_frame = self.detection_result.copy()

        # Apply privacy mode if enabled
        if self.privacy_mode and self.bboxes:
            display_frame = apply_pixelation(display_frame, self.bboxes)

        # Get the original frame dimensions
        original_height, original_width = display_frame.shape[:2]

        # Calculate scale factor for text size based on current display size
        # This ensures HUD elements scale appropriately
        scale_factor = max(1.0, original_width / 640.0)  # Use 640 as a reference size

        # Draw detection information with appropriate text size
        display_frame = draw_detection_info(
            display_frame,
            self.num_faces,
            self.fps,
            self.face_threshold,
            self.alert_active,
            text_scale=scale_factor  # Pass scale factor to drawing function
        )

        # Convert to QPixmap
        pixmap = cv_to_pixmap(display_frame)

        # Scale the pixmap to fit the label size while maintaining aspect ratio
        label_size = self.webcam_label.size()
        scaled_pixmap = pixmap.scaled(
            label_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Set the pixmap in the label
        self.webcam_label.setPixmap(scaled_pixmap)
    
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
    
    def _on_snapshot_clicked(self):
        """Handle snapshot button click."""
        if self.current_frame is not None:
            # Get timestamp for filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"eyesoff_snapshot_{timestamp}.jpg"
            
            # Save current display frame
            if self.detection_result is not None:
                cv2.imwrite(filename, self.detection_result)
                
                # You could add a notification here to tell the user the snapshot was saved
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