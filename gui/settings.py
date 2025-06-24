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
        #self.tabs.addTab(self._create_alert_tab(), "Alert")
        self.tabs.addTab(self._create_camera_tab(), "Camera")
        self.tabs.addTab(self._create_app_tab(), "Application")
        self.tabs.addTab(self._create_advanced_tab(), "Advanced")
        
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

        # Alert threshold group
        behaviour_group = QGroupBox("Alert Behaviour")
        behaviour_layout = QFormLayout()

        self.alert_sensitivity_slider = QSlider(Qt.Horizontal)
        self.alert_sensitivity_slider.setRange(0, 100)
        self.alert_sensitivity_slider.setSingleStep(1)
        self.alert_sensitivity_slider.setValue(80)

        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("Low"))
        labels_layout.addStretch()
        labels_layout.addWidget(QLabel("Medium"))
        labels_layout.addStretch()
        labels_layout.addWidget(QLabel("High"))

        container_layout = QVBoxLayout()
        container_layout.addWidget(self.alert_sensitivity_slider)
        container_layout.addLayout(labels_layout)

        behaviour_layout.addRow("Certainty Required to Alert:", container_layout)

        # Face threshold spinbox
        self.face_threshold_spin = QSpinBox()
        self.face_threshold_spin.setRange(1, 10)
        self.face_threshold_spin.setToolTip("Number of faces that will trigger the alert")
        behaviour_layout.addRow("Face Count Threshold:", self.face_threshold_spin)

        # Auto-dismiss
        self.auto_dismiss_check = QCheckBox()
        behaviour_layout.addRow("Auto-dismiss Alert?", self.auto_dismiss_check)

        behaviour_group.setLayout(behaviour_layout)

        # Alert Type Selection Group
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

        # Push Notification Settings Group
        self.push_notification_group = QGroupBox("Push Notification Settings")
        push_notification_layout = QFormLayout()
        push_notification_layout.setVerticalSpacing(12)

        # Launch app checkbox
        self.launch_app_check = QCheckBox()
        self.launch_app_check.toggled.connect(self._on_launch_app_toggled)
        push_notification_layout.addRow("Launch External App:", self.launch_app_check)

        # App selection
        app_path_layout = QHBoxLayout()
        self.app_path_edit = QLineEdit()
        self.app_path_edit.setEnabled(False)

        self.app_browse_button = QPushButton("Browse...")
        self.app_browse_button.setEnabled(False)
        self.app_browse_button.clicked.connect(self._on_app_browse_clicked)

        app_path_layout.addWidget(self.app_path_edit)
        app_path_layout.addWidget(self.app_browse_button)
        push_notification_layout.addRow("Application to Laucnh:", app_path_layout)

        self.push_notification_group.setLayout(push_notification_layout)

        # Screen Alert Settings Group
        self.screen_alert_group = QGroupBox("Screen Alert Settings")
        screen_alert_layout = QFormLayout()
        screen_alert_layout.setVerticalSpacing(12)

        # Alert text
        self.alert_text_edit = QLineEdit()
        screen_alert_layout.addRow("Alert Message:", self.alert_text_edit)

        # Color selection
        self.alert_color_button = ColorButton()
        self.alert_color_button.color_changed.connect(self._on_alert_color_changed)
        screen_alert_layout.addRow("Alert Color:", self.alert_color_button)

        # Fullscreen mode
        self.fullscreen_check = QCheckBox()
        self.fullscreen_check.setToolTip("Display alert in fullscreen mode (covers entire screen)")
        screen_alert_layout.addRow("Fullscreen Mode:", self.fullscreen_check)

        self.screen_alert_group.setLayout(screen_alert_layout)

        # Sound Settings Group (shared for both alert types)
        sound_group = QGroupBox("Sound Settings")
        sound_layout = QFormLayout()
        sound_layout.setVerticalSpacing(12)

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

        # Add all groups to tab layout
        layout.addWidget(behaviour_group)
        layout.addWidget(alert_type_group)
        layout.addWidget(self.push_notification_group)
        layout.addWidget(self.screen_alert_group)
        layout.addWidget(sound_group)
        layout.addStretch(1)

        tab.setLayout(layout)
        return tab

    def _on_alert_type_changed(self):
        """Handle alert type radio button change."""
        use_screen_alert = self.screen_alert_radio.isChecked()
        use_notification = self.notification_radio.isChecked()

        # Show/hide the appropriate settings groups
        self.screen_alert_group.setVisible(use_screen_alert)
        self.push_notification_group.setVisible(use_notification)

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
        
        # Add all groups to tab layout
        layout.addWidget(camera_group)
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
        layout.addWidget(snapshot_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab

    def _create_advanced_tab(self) -> QWidget:
        """
            Create the advanced settings tab.

            Returns:
                QWidget: Advanced settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()

        # TODO - Make the settings simpler
        # ADD Advanced settings from here on out -
        advanced_detection_group = QGroupBox("Model")
        advanced_detection_layout = QFormLayout()

        # Model type combo box
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(list(self.MODEL_TYPE_MAPPING.keys()))
        self.model_type_combo.currentTextChanged.connect(self._on_model_type_changed)
        self.model_type_combo.setToolTip(
            '"Face" detects only when faces enter the frame | "Gaze" detects when people are looking at your screen')
        advanced_detection_layout.addRow("Model Type:", self.model_type_combo)

        # Model selection combo box
        self.model_path_combo = QComboBox()

        advanced_detection_group.setLayout(advanced_detection_layout)

        # Alert threshold group
        threshold_group = QGroupBox("Alert")
        threshold_layout = QFormLayout()

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

        self.alert_opacity_spin = QSpinBox()
        self.alert_opacity_spin.setRange(10, 100)
        self.alert_opacity_spin.setSuffix("%")
        threshold_layout.addRow("Opacity:", self.alert_opacity_spin)

        # Animation effects
        self.animations_check = QCheckBox()
        threshold_layout.addRow("Animation Effects:", self.animations_check)

        # Width
        self.alert_width_spin = QSpinBox()
        self.alert_width_spin.setRange(200, 1200)
        self.alert_width_spin.setSingleStep(50)
        threshold_layout.addRow("Width:", self.alert_width_spin)

        # Height
        self.alert_height_spin = QSpinBox()
        self.alert_height_spin.setRange(100, 800)
        self.alert_height_spin.setSingleStep(50)
        threshold_layout.addRow("Height:", self.alert_height_spin)

        threshold_group.setLayout(threshold_layout)


        # Add all groups to tab layout
        layout.addWidget(advanced_detection_group)
        layout.addWidget(threshold_group)
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

            self._on_model_type_changed(friendly_name)  # Populate model path combo

            model_path = self.config_manager.get("model_path", "")
            index = self.model_path_combo.findText(model_path)
            if index >= 0:
                self.model_path_combo.setCurrentIndex(index)

            self.face_threshold_spin.setValue(self.config_manager.get("face_threshold", 1))
            self.debounce_spin.setValue(self.config_manager.get("debounce_time", 1.0))
            self.detection_delay_spin.setValue(self.config_manager.get("detection_delay", 0.2))
            # Load gaze threshold
            gaze_threshold = self.config_manager.get("gaze_threshold", 0.6)
            self.alert_sensitivity_slider.setValue(self._threshold_to_slider(gaze_threshold))

            # Alert tab
            # Set the appropriate radio button based on alert_on setting
            alert_on = self.config_manager.get("alert_on", False)
            if alert_on:
                self.screen_alert_radio.setChecked(True)
            else:
                self.notification_radio.setChecked(True)

            # Show/hide configurations based on alert type
            self.screen_alert_group.setVisible(alert_on)
            self.push_notification_group.setVisible(not alert_on)  # Only show for push notifications

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

    def _slider_to_threshold(self, slider_value):
        """Convert slider value (0-100) to threshold (0.0-1.0)"""
        return slider_value / 100.0

    def _threshold_to_slider(self, threshold):
        """Convert threshold (0.0-1.0) to slider value (0-100)"""
        return int(threshold * 100)

    def _gaze_to_face_threshold(self, gaze_confidence):
        face_threshold = min(gaze_confidence * 1.2, 0.95)  # cap face threshold to 0.95

        return face_threshold

    def _get_current_settings(self):
        """Get current settings from UI without saving them."""
        settings = {}

        gaze_threshold_value = self._slider_to_threshold(self.alert_sensitivity_slider.value())

        # Detection tab
        settings["detector_type"] = self.MODEL_TYPE_MAPPING.get(self.model_type_combo.currentText(), "yunet")
        settings["model_path"] = self.model_path_combo.currentText()
        # Confidence threshold is a measure of how confident we are something is a face - it is now linked to the gaze_threshold.
        settings["confidence_threshold"] = self._gaze_to_face_threshold(gaze_threshold_value)
        settings["gaze_threshold"] = gaze_threshold_value
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

        # App tab
        settings["snapshot_path"] = self.path_edit.text()

        return settings

    def apply_settings(self):
        """Apply current UI settings to config manager."""
        settings = self._get_current_settings()

        # Update configuration
        self.config_manager.update(settings)
        self.config_manager.save_config()

        return settings

    def reset_to_defaults(self):
        """Reset settings to defaults."""
        self.config_manager.reset_to_defaults()
        self._load_settings()
        return self.config_manager.get_all()
