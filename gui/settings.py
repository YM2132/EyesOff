import os
from typing import Dict, Any, List, Tuple

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QPushButton, QSlider, QLineEdit, QFileDialog, QGroupBox,
                             QFormLayout, QColorDialog, QGridLayout, QRadioButton)

from core.detector import FaceDetector
from core.webcam import WebcamManager
from utils.config import ConfigManager
from utils.platform import get_platform_manager


class ColorButton(QPushButton):
    """Button that displays a color and opens a color dialog when clicked."""
    
    color_changed = pyqtSignal(tuple)
    
    def __init__(self, color: Tuple[int, int, int] = (0, 0, 255), parent=None):
        """
        Initialize the color button.
        
        Args:
            color: Initial color in BGR format (B, G, R)
            parent: Parent widget
        """
        super().__init__(parent)
        self.bgr_color = color
        self._update_button_style()
        self.clicked.connect(self._on_clicked)
    
    def _update_button_style(self):
        """Update the button style based on the current color."""
        # Convert BGR to RGB for QColor
        r, g, b = self.bgr_color[2], self.bgr_color[1], self.bgr_color[0]
        
        # Calculate appropriate text color (black or white) based on brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = 'black' if brightness > 128 else 'white'
        
        # Use hex format for the background color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                min-width: 60px;
                min-height: 25px;
            }}
        """)
        
        # Add hex code to the button text
        self.setText(f"#{r:02x}{g:02x}{b:02x}")
    
    def set_color(self, color: Tuple[int, int, int]):
        """
        Set the button color.
        
        Args:
            color: New color in BGR format (B, G, R)
        """
        self.bgr_color = color
        self._update_button_style()
    
    def _on_clicked(self):
        """Handle button click to open color dialog."""
        # Convert BGR to RGB for QColorDialog
        r, g, b = self.bgr_color[2], self.bgr_color[1], self.bgr_color[0]
        initial = QColor(r, g, b)
        
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            # Convert RGB back to BGR for storage
            new_bgr = (color.blue(), color.green(), color.red())
            self.bgr_color = new_bgr
            self._update_button_style()
            self.color_changed.emit(new_bgr)


class SettingsPanel(QWidget):
    """
    Settings panel for the EyesOff application.
    Provides controls to adjust all application settings.
    """
    
    # Signal emitted when settings are changed
    settings_changed = pyqtSignal(dict)

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the settings panel.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.platform_manager = get_platform_manager()
        self.available_models = FaceDetector.get_available_models()
        self.available_cameras = WebcamManager.get_device_list()

        # Define mapping between user-friendly names and internal model types
        self.MODEL_TYPE_MAPPING = {
            "Face": "yunet",
            "Gaze": "gaze"
        }

        # Reverse mapping (for loading settings)
        self.REVERSE_MODEL_TYPE_MAPPING = {v: k for k, v in self.MODEL_TYPE_MAPPING.items()}
        
        # Initialize UI
        self._init_ui()
        
        # Load initial settings
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create the various setting tabs
        self.tabs.addTab(self._create_detection_tab(), "Detection")
        self.tabs.addTab(self._create_alert_tab(), "Alert")
        self.tabs.addTab(self._create_camera_tab(), "Camera")
        self.tabs.addTab(self._create_app_tab(), "Application")
        
        # Add components to main layout
        main_layout.addWidget(self.tabs)

        self.setLayout(main_layout)

        self._auto_connect_signals()

    def _auto_connect_signals(self):
        """Automatically connect change signals from all input widgets."""
        # Map widget types to their change signals
        signal_map = {
            QComboBox: 'currentTextChanged',
            QSpinBox: 'valueChanged',
            QDoubleSpinBox: 'valueChanged',
            QCheckBox: 'toggled',
            QRadioButton: 'toggled',
            QLineEdit: 'textChanged',
            QSlider: 'valueChanged',
            ColorButton: 'color_changed'  # Your custom widget
        }

        # Find all widgets and connect their signals
        for widget in self.findChildren(QWidget):
            widget_type = type(widget)

            # Check if this widget type has a known change signal
            for widget_class, signal_name in signal_map.items():
                if isinstance(widget, widget_class):
                    # Skip buttons that aren't radio buttons
                    if isinstance(widget, QPushButton) and not isinstance(widget, QRadioButton):
                        continue

                    # Connect the signal
                    signal = getattr(widget, signal_name, None)
                    if signal:
                        signal.connect(self._on_any_setting_changed)
                    break

    def _on_any_setting_changed(self):
        """Emit settings_changed signal when any setting is modified."""
        # Only emit if we're not currently loading settings
        if hasattr(self, '_loading_settings') and self._loading_settings:
            return

        # Enable apply button
        if hasattr(self, 'apply_button'):
            self.apply_button.setEnabled(True)

        # Emit a simple signal without the full settings dict
        # The receiver can call get_current_settings() if needed
        self.settings_changed.emit({})

    
    def _create_detection_tab(self) -> QWidget:
        """
        Create the detection settings tab.
        
        Returns:
            QWidget: Detection settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Model selection group
        model_group = QGroupBox("Detection Model")
        model_layout = QFormLayout()
        
        # Model type combo box
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(list(self.MODEL_TYPE_MAPPING.keys()))
        self.model_type_combo.currentTextChanged.connect(self._on_model_type_changed)
        self.model_type_combo.setToolTip('"Face" detects only when faces enter the frame | "Gaze" detects when people are looking at your screen')
        model_layout.addRow("Model Type:", self.model_type_combo)
        
        # Model selection combo box
        self.model_path_combo = QComboBox()

        # Face confidence threshold
        self.face_confidence_spin = QDoubleSpinBox()
        self.face_confidence_spin.setRange(0.1, 1.0)
        self.face_confidence_spin.setSingleStep(0.05)
        self.face_confidence_spin.setDecimals(2)
        self.face_confidence_spin.setValue(0.75)  # Default value
        self.face_confidence_spin.setToolTip("Minimum confidence threshold for face detection")
        model_layout.addRow("Face Confidence Threshold:", self.face_confidence_spin)

        # Gaze confidence threshold
        self.gaze_confidence_spin = QDoubleSpinBox()
        self.gaze_confidence_spin.setRange(0.1, 1.0)
        self.gaze_confidence_spin.setSingleStep(0.05)
        self.gaze_confidence_spin.setDecimals(2)
        self.gaze_confidence_spin.setValue(0.6)  # Default value
        self.gaze_confidence_spin.setToolTip("Threshold to determine if someone is looking at the screen")
        model_layout.addRow("Gaze Confidence Threshold:", self.gaze_confidence_spin)
        
        model_group.setLayout(model_layout)
        
        # Alert threshold group
        threshold_group = QGroupBox("Alert Threshold")
        threshold_layout = QFormLayout()
        
        # Face threshold spinbox
        self.face_threshold_spin = QSpinBox()
        self.face_threshold_spin.setRange(1, 10)
        self.face_threshold_spin.setToolTip("Number of faces that will trigger the alert")
        threshold_layout.addRow("Face Count Threshold:", self.face_threshold_spin)
        
        # Debounce time
        self.debounce_spin = QDoubleSpinBox()
        self.debounce_spin.setRange(0.1, 5.0)
        self.debounce_spin.setSingleStep(0.1)
        self.debounce_spin.setDecimals(1)
        self.debounce_spin.setToolTip("Time in seconds to wait before changing alert state")
        threshold_layout.addRow("Debounce Time (s):", self.debounce_spin)
        
        # Detection verification delay
        self.detection_delay_spin = QDoubleSpinBox()
        self.detection_delay_spin.setRange(0.0, 2.0)
        self.detection_delay_spin.setSingleStep(0.05)
        self.detection_delay_spin.setDecimals(2)
        self.detection_delay_spin.setValue(0.2)
        self.detection_delay_spin.setToolTip("Time to confirm detection before showing alert")
        threshold_layout.addRow("Detection Delay (s):", self.detection_delay_spin)
        
        threshold_group.setLayout(threshold_layout)
        
        # Add all groups to tab layout
        layout.addWidget(model_group)
        layout.addWidget(threshold_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab

    def _create_alert_tab(self) -> QWidget:
        """
        Create the alert settings tab with improved UX.

        Returns:
            QWidget: Alert settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 1. Alert Type Selection (Radio Buttons)
        alert_type_group = QGroupBox("Alert Type")
        alert_type_layout = QVBoxLayout()
        alert_type_layout.setSpacing(10)

        # Create radio buttons for the two options
        self.notification_radio = QRadioButton("Push Notification")
        self.notification_radio.setToolTip("Show a brief system notification in the corner")

        self.screen_alert_radio = QRadioButton("Screen Alert")
        self.screen_alert_radio.setToolTip("Show an attention-grabbing overlay on screen")

        # Add radio buttons to layout
        alert_type_layout.addWidget(self.notification_radio)
        alert_type_layout.addWidget(self.screen_alert_radio)
        alert_type_group.setLayout(alert_type_layout)

        # Connect radio buttons to handler
        self.notification_radio.toggled.connect(self._on_alert_type_changed)
        self.screen_alert_radio.toggled.connect(self._on_alert_type_changed)

        # 2. Screen Alert Configuration
        self.screen_alert_config = QGroupBox("Configure Screen Alert")
        screen_alert_layout = QFormLayout()
        screen_alert_layout.setVerticalSpacing(12)

        # Alert text
        self.alert_text_edit = QLineEdit()
        screen_alert_layout.addRow("Text:", self.alert_text_edit)

        # Appearance with color and opacity - improved alignment
        appearance_layout = QGridLayout()  # Use grid for better alignment
        appearance_layout.setSpacing(10)

        # Color in first column
        appearance_layout.addWidget(QLabel("Color:"), 0, 0, Qt.AlignRight)
        self.alert_color_button = ColorButton()
        self.alert_color_button.color_changed.connect(self._on_alert_color_changed)
        self.alert_color_button.setMinimumWidth(0)  # Ensure consistent width
        appearance_layout.addWidget(self.alert_color_button, 0, 1)

        # Opacity in second column, properly aligned
        appearance_layout.addWidget(QLabel("Opacity:"), 0, 2, Qt.AlignRight)
        self.alert_opacity_spin = QSpinBox()
        self.alert_opacity_spin.setRange(10, 100)
        self.alert_opacity_spin.setSuffix("%")
        self.alert_opacity_spin.setMinimumWidth(0)
        appearance_layout.addWidget(self.alert_opacity_spin, 0, 3)

        # Add some stretching to keep alignment
        appearance_layout.setColumnStretch(4, 1)

        screen_alert_layout.addRow("Appearance:", appearance_layout)

        # Display Options
        display_options_group = QGroupBox("Display Options")
        display_options_layout = QVBoxLayout()
        display_options_layout.setContentsMargins(12, 12, 12, 12)  # Add more padding
        display_options_layout.setSpacing(10)  # Increase spacing between elements

        # Set minimum height to ensure it's larger
        display_options_group.setMinimumHeight(0)  # Slightly taller to accommodate added controls

        # Animation effects
        self.animations_check = QCheckBox("Animation effects")
        display_options_layout.addWidget(self.animations_check)

        # Fullscreen mode
        self.fullscreen_check = QCheckBox("Fullscreen mode")
        self.fullscreen_check.setToolTip("Display alert in fullscreen mode (covers entire screen)")
        display_options_layout.addWidget(self.fullscreen_check)

        # Size controls
        size_layout = QGridLayout()
        size_layout.setHorizontalSpacing(10)
        size_layout.setVerticalSpacing(10)

        # Add label in its own column
        size_layout.addWidget(QLabel("Size:"), 0, 0, Qt.AlignRight)

        # Width controls
        size_layout.addWidget(QLabel("Width:"), 0, 1)
        self.alert_width_spin = QSpinBox()
        self.alert_width_spin.setRange(200, 1200)
        self.alert_width_spin.setSingleStep(50)
        self.alert_width_spin.setMinimumHeight(18)
        size_layout.addWidget(self.alert_width_spin, 0, 2)

        # Height controls
        size_layout.addWidget(QLabel("Height:"), 0, 3)
        self.alert_height_spin = QSpinBox()
        self.alert_height_spin.setRange(100, 800)
        self.alert_height_spin.setSingleStep(50)
        self.alert_height_spin.setMinimumHeight(18)
        size_layout.addWidget(self.alert_height_spin, 0, 4)

        # Add stretch to maintain alignment
        size_layout.setColumnStretch(5, 1)
        display_options_layout.addLayout(size_layout)

        # Auto-dismiss control - MOVED here inside the Display Options
        auto_dismiss_layout = QHBoxLayout()
        self.auto_dismiss_check = QCheckBox("Auto-dismiss alert?")
        auto_dismiss_layout.addWidget(self.auto_dismiss_check)
        auto_dismiss_layout.addStretch(1)
        display_options_layout.addLayout(auto_dismiss_layout)

        auto_dismiss_layout.addStretch(1)
        display_options_layout.addLayout(auto_dismiss_layout)

        display_options_group.setLayout(display_options_layout)
        screen_alert_layout.addRow(display_options_group)

        self.screen_alert_config.setLayout(screen_alert_layout)

        # 3. Sound Settings (Common for both alert types)
        sound_group = QGroupBox("Sound Settings")
        sound_layout = QFormLayout()

        # Play sound checkbox
        self.alert_sound_check = QCheckBox()
        self.alert_sound_check.toggled.connect(self._on_alert_sound_toggled)
        sound_layout.addRow("Play Sound:", self.alert_sound_check)

        # Sound file selection
        sound_file_layout = QHBoxLayout()
        self.alert_sound_edit = QLineEdit()
        self.alert_sound_edit.setEnabled(False)

        self.sound_browse_button = QPushButton("Browse...")
        self.sound_browse_button.setEnabled(False)
        self.sound_browse_button.clicked.connect(self._on_sound_browse_clicked)

        sound_file_layout.addWidget(self.alert_sound_edit)
        sound_file_layout.addWidget(self.sound_browse_button)

        sound_layout.addRow("Sound File:", sound_file_layout)
        sound_group.setLayout(sound_layout)

        # 4. Application Launch (Only for Push Notifications)
        self.app_launch_group = QGroupBox("Launch External Application")
        app_launch_layout = QVBoxLayout()

        # Launch app checkbox
        self.launch_app_check = QCheckBox("Launch application when alert triggered")
        self.launch_app_check.toggled.connect(self._on_launch_app_toggled)
        app_launch_layout.addWidget(self.launch_app_check)

        # App selection
        app_path_layout = QHBoxLayout()
        app_path_layout.addWidget(QLabel("Application:"))
        self.app_path_edit = QLineEdit()
        self.app_path_edit.setEnabled(False)
        app_path_layout.addWidget(self.app_path_edit)

        self.app_browse_button = QPushButton("Browse...")
        self.app_browse_button.setEnabled(False)
        self.app_browse_button.clicked.connect(self._on_app_browse_clicked)
        app_path_layout.addWidget(self.app_browse_button)

        app_launch_layout.addLayout(app_path_layout)
        self.app_launch_group.setLayout(app_launch_layout)

        # Add all groups to tab layout
        layout.addWidget(alert_type_group)
        layout.addWidget(self.screen_alert_config)
        layout.addWidget(sound_group)
        layout.addWidget(self.app_launch_group)
        layout.addStretch(1)

        tab.setLayout(layout)
        return tab

    def _on_alert_type_changed(self):
        """Handle alert type radio button change."""
        use_screen_alert = self.screen_alert_radio.isChecked()
        use_notification = self.notification_radio.isChecked()

        # Show/hide the screen alert configuration based on selection
        self.screen_alert_config.setVisible(use_screen_alert)

        # Show/hide the app launch group based on selection
        # Only show app launch for push notifications, NOT for screen alerts
        self.app_launch_group.setVisible(use_notification)

        # Update internal state
        if hasattr(self, 'alert_on_check'):  # For backward compatibility
            self.alert_on_check.setChecked(use_screen_alert)
    
    def _create_camera_tab(self) -> QWidget:
        """
        Create the camera settings tab.
        
        Returns:
            QWidget: Camera settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Camera selection group
        camera_group = QGroupBox("Camera Selection")
        camera_layout = QFormLayout()
        
        # Camera device combo box
        self.camera_combo = QComboBox()
        # Get available cameras
        for cam_idx in self.available_cameras:
            self.camera_combo.addItems([f"Camera {cam_idx}"])
        camera_layout.addRow("Camera Device:", self.camera_combo)
        
        camera_group.setLayout(camera_layout)
        
        # Resolution group
        resolution_group = QGroupBox("Resolution")
        resolution_layout = QFormLayout()
        
        # Common resolutions
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "640x480 (VGA)", 
            "1280x720 (HD)", 
            "1920x1080 (Full HD)",
            "Custom"
        ])
        self.resolution_combo.currentTextChanged.connect(self._on_resolution_changed)
        resolution_layout.addRow("Preset:", self.resolution_combo)
        
        # Custom resolution
        custom_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(320, 3840)
        self.width_spin.setSingleStep(80)
        self.width_spin.setEnabled(False)  # Initially disabled
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(240, 2160)
        self.height_spin.setSingleStep(60)
        self.height_spin.setEnabled(False)  # Initially disabled
        
        custom_layout.addWidget(QLabel("Width:"))
        custom_layout.addWidget(self.width_spin)
        custom_layout.addWidget(QLabel("Height:"))
        custom_layout.addWidget(self.height_spin)
        
        resolution_layout.addRow("Custom:", custom_layout)
        
        resolution_group.setLayout(resolution_layout)
        
        # Add all groups to tab layout
        layout.addWidget(camera_group)
        layout.addWidget(resolution_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab
    
    def _create_app_tab(self) -> QWidget:
        """
        Create the application settings tab.
        
        Returns:
            QWidget: Application settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()

        # TODO - Reactivate these components and make them work
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout()
        
        # Start at boot
        self.start_boot_check = QCheckBox()
        startup_layout.addRow("Start on System Boot:", self.start_boot_check)
        
        # Start minimized
        self.start_minimized_check = QCheckBox()
        startup_layout.addRow("Start Minimized:", self.start_minimized_check)
        
        #startup_group.setLayout(startup_layout)
        
        # UI settings group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()
        
        # Always on top
        self.always_top_check = QCheckBox()
        ui_layout.addRow("Always on Top:", self.always_top_check)
        
        # Minimize to tray
        self.minimize_tray_check = QCheckBox()
        ui_layout.addRow("Minimize to System Tray:", self.minimize_tray_check)
        
        #ui_group.setLayout(ui_layout)

        # Snapshot saving path group
        snapshot_group = QGroupBox("Path to save snapshots")
        snapshot_layout = QFormLayout()

        # Selection for path to save snapshots
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()

        path_browse_button = QPushButton("Browse...")
        path_browse_button.clicked.connect(self._on_path_browse_clicked)

        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_browse_button)

        snapshot_layout.addRow("Path:", path_layout)

        snapshot_group.setLayout(snapshot_layout)
        
        # Add all groups to tab layout
        #layout.addWidget(startup_group)
        #layout.addWidget(ui_group)
        layout.addWidget(snapshot_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab

    def _load_settings(self):
        """Load settings from configuration manager into UI components."""
        # Set flag to prevent emitting signals while loading
        self._loading_settings = True

        try:
            # Detection tab
            detector_type = self.config_manager.get("detector_type", "yunet")
            friendly_name = self.REVERSE_MODEL_TYPE_MAPPING.get(detector_type, "Face")

            self.model_type_combo.setCurrentText(friendly_name)

            # Explicitly enable/disable gaze threshold control based on detector type
            self.gaze_confidence_spin.setEnabled(detector_type == "gaze")

            self._on_model_type_changed(friendly_name)  # Populate model path combo

            model_path = self.config_manager.get("model_path", "")
            index = self.model_path_combo.findText(model_path)
            if index >= 0:
                self.model_path_combo.setCurrentIndex(index)

            # self.confidence_spin.setValue(self.config_manager.get("confidence_threshold", 0.5))
            self.face_confidence_spin.setValue(self.config_manager.get("confidence_threshold", 0.75))
            self.face_threshold_spin.setValue(self.config_manager.get("face_threshold", 1))
            self.debounce_spin.setValue(self.config_manager.get("debounce_time", 1.0))
            self.detection_delay_spin.setValue(self.config_manager.get("detection_delay", 0.2))
            # Load gaze threshold
            self.gaze_confidence_spin.setValue(self.config_manager.get("gaze_threshold", 0.6))
            # self.show_detection_check.setChecked(self.config_manager.get("show_detection_visualization", True))
            # self.privacy_mode_check.setChecked(self.config_manager.get("privacy_mode", False))

            # Alert tab
            # Set the appropriate radio button based on alert_on setting
            alert_on = self.config_manager.get("alert_on", False)
            if alert_on:
                self.screen_alert_radio.setChecked(True)
            else:
                self.notification_radio.setChecked(True)

            # Show/hide configurations based on alert type
            self.screen_alert_config.setVisible(alert_on)
            self.app_launch_group.setVisible(not alert_on)  # Only show for push notifications

            # Change from slider to spinner for opacity
            opacity_percentage = int(self.config_manager.get("alert_opacity", 0.8) * 100)
            self.alert_opacity_spin.setValue(opacity_percentage)

            self.alert_text_edit.setText(self.config_manager.get("alert_text", "EYES OFF!!!"))
            self.alert_color_button.set_color(self.config_manager.get("alert_color", (0, 0, 255)))
            self.alert_opacity_spin.setValue(int(self.config_manager.get("alert_opacity", 0.8) * 100))

            alert_size = self.config_manager.get("alert_size", (600, 300))
            self.alert_width_spin.setValue(alert_size[0])
            self.alert_height_spin.setValue(alert_size[1])

            self.animations_check.setChecked(self.config_manager.get("enable_animations", True))
            self.fullscreen_check.setChecked(self.config_manager.get("fullscreen_mode", False))

            auto_dismiss = self.config_manager.get("auto_dismiss", False)
            self.auto_dismiss_check.setChecked(auto_dismiss)

            alert_sound_enabled = self.config_manager.get("alert_sound_enabled", False)
            self.alert_sound_check.setChecked(alert_sound_enabled)
            self.alert_sound_edit.setEnabled(alert_sound_enabled)
            self.sound_browse_button.setEnabled(alert_sound_enabled)
            self.alert_sound_edit.setText(self.config_manager.get("alert_sound_file", ""))

            # App launch settings
            self.launch_app_check.setChecked(self.config_manager.get("launch_app_enabled", False))
            self.app_path_edit.setText(self.config_manager.get("launch_app_path", ""))
            self.app_path_edit.setEnabled(self.launch_app_check.isChecked())
            self.app_browse_button.setEnabled(self.launch_app_check.isChecked())

            # Camera tab
            camera_id = self.config_manager.get("camera_id", 0)
            try:
                self.camera_combo.setCurrentIndex(camera_id)
            except:
                self.camera_combo.setCurrentIndex(0)

            frame_width = self.config_manager.get("frame_width", 640)
            frame_height = self.config_manager.get("frame_height", 480)

            # Set resolution combo
            if frame_width == 640 and frame_height == 480:
                self.resolution_combo.setCurrentText("640x480 (VGA)")
            elif frame_width == 1280 and frame_height == 720:
                self.resolution_combo.setCurrentText("1280x720 (HD)")
            elif frame_width == 1920 and frame_height == 1080:
                self.resolution_combo.setCurrentText("1920x1080 (Full HD)")
            else:
                self.resolution_combo.setCurrentText("Custom")
                self.width_spin.setEnabled(True)
                self.height_spin.setEnabled(True)
                self.width_spin.setValue(frame_width)
                self.height_spin.setValue(frame_height)

            # App tab
            self.start_boot_check.setChecked(self.config_manager.get("start_on_boot", False))
            self.start_minimized_check.setChecked(self.config_manager.get("start_minimized", False))
            self.always_top_check.setChecked(self.config_manager.get("always_on_top", False))
            self.minimize_tray_check.setChecked(self.config_manager.get("minimize_to_tray", True))
            # Add setting for getting the snapshot path
            self.path_edit.setText(self.config_manager.get("snapshot_path", ""))

        finally:
            self._loading_settings = False

    # TODO - should this function only be called upon apply?
    def _on_model_type_changed(self, user_model_name: str):
        """
        Handle model type change.
        
        Args:
            model_type: New model type
        """
        # Convert friendly name to internal model type
        model_type = self.MODEL_TYPE_MAPPING.get(user_model_name, "yunet")  # Default to yunet if not found

        # Clear and repopulate model path combo
        self.model_path_combo.clear()
        
        if model_type in self.available_models and self.available_models[model_type]:
            self.model_path_combo.addItems(self.available_models[model_type])
    
    def _on_alert_sound_toggled(self, checked: bool):
        """
        Handle alert sound checkbox toggle.
        
        Args:
            checked: New checkbox state
        """
        self.alert_sound_edit.setEnabled(checked)
        self.sound_browse_button.setEnabled(checked)
    
    def _on_sound_browse_clicked(self):
        """Handle sound file browse button click."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Alert Sound", "", "Sound Files (*.wav *.mp3);;All Files (*)"
        )
        
        if filename:
            self.alert_sound_edit.setText(filename)

    def _on_path_browse_clicked(self):
        """Handle sound file browse button click."""
        filename = QFileDialog.getExistingDirectory(
            self, "Select Directory", "", QFileDialog.ShowDirsOnly
        )

        if filename:
            self.path_edit.setText(filename)
    
    def _on_resolution_changed(self, resolution_text: str):
        """
        Handle resolution combo change.
        
        Args:
            resolution_text: New resolution text
        """
        # Enable/disable custom fields
        custom_enabled = resolution_text == "Custom"
        self.width_spin.setEnabled(custom_enabled)
        self.height_spin.setEnabled(custom_enabled)
        
        # Set default values for presets
        if resolution_text == "640x480 (VGA)":
            self.width_spin.setValue(640)
            self.height_spin.setValue(480)
        elif resolution_text == "1280x720 (HD)":
            self.width_spin.setValue(1280)
            self.height_spin.setValue(720)
        elif resolution_text == "1920x1080 (Full HD)":
            self.width_spin.setValue(1920)
            self.height_spin.setValue(1080)
    
    def _on_alert_color_changed(self, color: Tuple[int, int, int]):
        """
        Handle alert color change.
        
        Args:
            color: New color in BGR format
        """
        # Nothing needed here as the ColorButton handles the UI update
        pass

    def _on_alert_toggle_clicked(self, checked: bool):
        """Activate alert settings if we toggle the alert on"""
        self.appearance_group.setEnabled(checked)
        self.behavior_group.setEnabled(checked)

    def _on_launch_app_toggled(self, checked: bool):
        self.app_path_edit.setEnabled(checked)
        self.app_browse_button.setEnabled(checked)

    def _on_app_browse_clicked(self):
        """Handle app browse button click."""
        # Get platform-specific file filter
        file_filter = self.platform_manager.app_launcher.get_app_selection_filter()
        
        # Get default applications directory based on platform
        default_dir = "/Applications" if os.path.exists("/Applications") else os.path.expanduser("~")
        
        # Use platform-appropriate dialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Application",
            default_dir,
            file_filter + ";;All Files (*)"
        )

        # If nothing was selected, try directory selection as fallback
        if not filename:
            filename = QFileDialog.getExistingDirectory(
                self,
                "Select Application Directory",
                default_dir
            )

        # Validate and set the path
        if filename:
            # Validate using platform manager
            if self.platform_manager.app_launcher.validate_app_path(filename):
                self.app_path_edit.setText(filename)
            else:
                # Check if the selected path contains an executable
                if os.path.isdir(filename):
                    # Look for valid app files in the directory
                    app_files = []
                    for f in os.listdir(filename):
                        full_path = os.path.join(filename, f)
                        if self.platform_manager.app_launcher.validate_app_path(full_path):
                            app_files.append(f)
                    
                    if app_files:
                        # If directory contains app files, show a selection dialog
                        from PyQt5.QtWidgets import QInputDialog
                        app_name, ok = QInputDialog.getItem(
                            self,
                            "Select Application",
                            "Choose an application:",
                            app_files,
                            0,
                            False
                        )
                        if ok and app_name:
                            self.app_path_edit.setText(os.path.join(filename, app_name))
                    else:
                        from PyQt5.QtWidgets import QMessageBox
                        response = QMessageBox.question(
                            self,
                            "Confirm Selection",
                            f"The selected path doesn't appear to be an application.\n\n{filename}\n\nUse anyway?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if response == QMessageBox.Yes:
                            self.app_path_edit.setText(filename)

    def _get_current_settings(self):
        """Get current settings from UI without saving them."""
        settings = {}

        # Detection tab
        settings["detector_type"] = self.MODEL_TYPE_MAPPING.get(self.model_type_combo.currentText(), "yunet")
        settings["model_path"] = self.model_path_combo.currentText()
        settings["confidence_threshold"] = self.face_confidence_spin.value()
        settings["gaze_threshold"] = self.gaze_confidence_spin.value()
        settings["face_threshold"] = self.face_threshold_spin.value()
        settings["debounce_time"] = self.debounce_spin.value()
        settings["detection_delay"] = self.detection_delay_spin.value()

        # Alert tab
        settings["alert_on"] = self.screen_alert_radio.isChecked()
        settings["alert_opacity"] = self.alert_opacity_spin.value() / 100.0
        settings["alert_text"] = self.alert_text_edit.text()
        settings["alert_color"] = self.alert_color_button.bgr_color
        settings["alert_size"] = (self.alert_width_spin.value(), self.alert_height_spin.value())
        settings["alert_position"] = "centre"
        settings["enable_animations"] = self.animations_check.isChecked()
        settings["fullscreen_mode"] = self.fullscreen_check.isChecked()

        # App launch settings
        settings["launch_app_enabled"] = self.launch_app_check.isChecked()
        settings["launch_app_path"] = self.app_path_edit.text()

        settings["auto_dismiss"] = self.auto_dismiss_check.isChecked()
        if settings["auto_dismiss"]:
            settings["alert_duration"] = 1.0  # Fixed value
        else:
            settings["alert_duration"] = None

        settings["alert_sound_enabled"] = self.alert_sound_check.isChecked()
        settings["alert_sound_file"] = self.alert_sound_edit.text()

        # Camera tab
        settings["camera_id"] = self.camera_combo.currentIndex()

        if self.resolution_combo.currentText() == "Custom":
            settings["frame_width"] = self.width_spin.value()
            settings["frame_height"] = self.height_spin.value()
        else:
            if self.resolution_combo.currentText() == "640x480 (VGA)":
                settings["frame_width"] = 640
                settings["frame_height"] = 480
            elif self.resolution_combo.currentText() == "1280x720 (HD)":
                settings["frame_width"] = 1280
                settings["frame_height"] = 720
            elif self.resolution_combo.currentText() == "1920x1080 (Full HD)":
                settings["frame_width"] = 1920
                settings["frame_height"] = 1080

        # App tab
        settings["start_on_boot"] = self.start_boot_check.isChecked()
        settings["start_minimized"] = self.start_minimized_check.isChecked()
        settings["always_on_top"] = self.always_top_check.isChecked()
        settings["minimize_to_tray"] = self.minimize_tray_check.isChecked()
        settings["snapshot_path"] = self.path_edit.text()

        return settings

    def apply_settings(self):
        """Apply current UI settings to config manager."""
        settings = self._get_current_settings()

        # Update configuration
        self.config_manager.update(settings)
        self.config_manager.save_config()

        # Handle gaze confidence spin enable/disable
        if self.MODEL_TYPE_MAPPING.get(self.model_type_combo.currentText()) == 'gaze':
            self.gaze_confidence_spin.setEnabled(True)
        else:
            self.gaze_confidence_spin.setEnabled(False)

        return settings

    def reset_to_defaults(self):
        """Reset settings to defaults."""
        self.config_manager.reset_to_defaults()
        self._load_settings()
        return self.config_manager.get_all()
