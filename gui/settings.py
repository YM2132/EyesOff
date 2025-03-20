from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                           QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                           QPushButton, QSlider, QLineEdit, QFileDialog, QGroupBox,
                           QFormLayout, QColorDialog, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtGui import QColor

from typing import Dict, Any, List, Tuple
import os

from core.detector import FaceDetector
from core.webcam import WebcamManager
from utils.config import ConfigManager


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
    
    # Signal emitted when the "Test Alert" button is clicked
    test_alert_requested = pyqtSignal()
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the settings panel.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.available_models = FaceDetector.get_available_models()
        self.available_cameras = WebcamManager.get_device_list()
        
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
        
        # Add control buttons at the bottom
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._on_reset_clicked)
        
        self.test_alert_button = QPushButton("Test Alert")
        self.test_alert_button.clicked.connect(self._on_test_alert_clicked)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.test_alert_button)
        button_layout.addWidget(self.apply_button)
        
        # Add components to main layout
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _create_detection_tab(self) -> QWidget:
        """
        Create the detection settings tab.
        
        Returns:
            QWidget: Detection settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Model selection group
        model_group = QGroupBox("Face Detection Model")
        model_layout = QFormLayout()
        
        # Model type combo box
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["yunet"])  # Removed moondream as it's not fully developed yet
        self.model_type_combo.currentTextChanged.connect(self._on_model_type_changed)
        model_layout.addRow("Model Type:", self.model_type_combo)
        
        # Model selection combo box
        self.model_path_combo = QComboBox()
        # Will be populated in _on_model_type_changed
        #model_layout.addRow("Model:", self.model_path_combo)
        
        # Confidence threshold
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setDecimals(2)
        model_layout.addRow("Confidence Threshold:", self.confidence_spin)
        
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
        
        # Visualization group
        visual_group = QGroupBox("Visualization")
        visual_layout = QFormLayout()
        
        # Show detection visualization - Defined but doenst do anything
        # self.show_detection_check = QCheckBox()
        #self.show_detection_check.setToolTip("Show detection boundaries and information")
        #visual_layout.addRow("Show Detection Visualization:", self.show_detection_check)
        
        # Privacy mode
        self.privacy_mode_check = QCheckBox()
        self.privacy_mode_check.setToolTip("Blur or pixelate faces in the display")
        visual_layout.addRow("Privacy Mode:", self.privacy_mode_check)
        
        visual_group.setLayout(visual_layout)
        
        # Add all groups to tab layout
        layout.addWidget(model_group)
        layout.addWidget(threshold_group)
        layout.addWidget(visual_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab
    
    def _create_alert_tab(self) -> QWidget:
        """
        Create the alert settings tab.
        
        Returns:
            QWidget: Alert settings tab
        """
        tab = QWidget()
        layout = QVBoxLayout()

        self.alert_on_group = QGroupBox("Activate Alert")
        self.alert_on_layout = QFormLayout()

        # Alert or Notification only
        self.alert_on_check = QCheckBox()
        self.alert_on_check.toggled.connect(self._on_alert_toggle_clicked)
        self.alert_on_check.setToolTip("When checked, shows alert dialogs. When unchecked, shows only push notifications.")
        self.alert_on_layout.addRow("Alert Toggle:", self.alert_on_check)

        self.alert_on_group.setLayout(self.alert_on_layout)
        
        # Appearance group
        self.appearance_group = QGroupBox("Alert Appearance")
        self.appearance_layout = QFormLayout()
        self.appearance_group.setEnabled(False)
        
        # Alert text
        self.alert_text_edit = QLineEdit()
        self.appearance_layout.addRow("Alert Text:", self.alert_text_edit)
        
        # Alert color
        self.alert_color_button = ColorButton()
        self.alert_color_button.color_changed.connect(self._on_alert_color_changed)
        self.appearance_layout.addRow("Alert Color:", self.alert_color_button)
        
        # Alert opacity
        self.alert_opacity_slider = QSlider(Qt.Horizontal)
        self.alert_opacity_slider.setRange(10, 100)
        self.alert_opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.alert_opacity_slider.setTickInterval(10)
        self.appearance_layout.addRow("Opacity:", self.alert_opacity_slider)
        
        # Alert size
        size_layout = QHBoxLayout()
        self.alert_width_spin = QSpinBox()
        self.alert_width_spin.setRange(200, 1200)
        self.alert_width_spin.setSingleStep(50)
        
        self.alert_height_spin = QSpinBox()
        self.alert_height_spin.setRange(100, 800)
        self.alert_height_spin.setSingleStep(50)
        
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.alert_width_spin)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.alert_height_spin)
        
        self.appearance_layout.addRow("Alert Size:", size_layout)
        
        # Alert position
        self.alert_position_combo = QComboBox()
        self.alert_position_combo.addItems(["center", "top", "bottom"])
        self.appearance_layout.addRow("Alert Position:", self.alert_position_combo)
        
        self.appearance_group.setLayout(self.appearance_layout)
        
        # Behavior group
        self.behavior_group = QGroupBox("Alert Behavior")
        self.behavior_layout = QFormLayout()
        self.behavior_group.setEnabled(False)
        
        # Enable animations
        self.animations_check = QCheckBox()
        self.behavior_layout.addRow("Enable Animations:", self.animations_check)
        
        # Auto-dismiss
        self.auto_dismiss_check = QCheckBox()
        self.auto_dismiss_check.toggled.connect(self._on_auto_dismiss_toggled)
        self.behavior_layout.addRow("Auto-dismiss Alert:", self.auto_dismiss_check)
        
        # Alert duration
        self.alert_duration_spin = QDoubleSpinBox()
        self.alert_duration_spin.setRange(1.0, 30.0)
        self.alert_duration_spin.setSingleStep(0.5)
        self.alert_duration_spin.setDecimals(1)
        self.alert_duration_spin.setEnabled(False)  # Initially disabled
        self.behavior_layout.addRow("Alert Duration (s):", self.alert_duration_spin)
        
        # Fullscreen mode
        self.fullscreen_check = QCheckBox()
        self.fullscreen_check.setToolTip("Display alert in fullscreen mode (covers entire screen)")
        self.behavior_layout.addRow("Fullscreen Alert:", self.fullscreen_check)
        
        # Native notifications - removing since we're using automatic hybrid approach
        # We'll keep the setting in the config but hide it from the UI
        self.native_notifications_check = QCheckBox()
        self.native_notifications_check.setVisible(False)  # Hide from UI
        
        # Alert sound
        self.alert_sound_check = QCheckBox()
        self.alert_sound_check.toggled.connect(self._on_alert_sound_toggled)
        self.behavior_layout.addRow("Play Alert Sound:", self.alert_sound_check)
        
        # Sound file selection
        sound_layout = QHBoxLayout()
        self.alert_sound_edit = QLineEdit()
        self.alert_sound_edit.setEnabled(False)  # Initially disabled
        
        self.sound_browse_button = QPushButton("Browse...")
        self.sound_browse_button.setEnabled(False)  # Initially disabled
        self.sound_browse_button.clicked.connect(self._on_sound_browse_clicked)
        
        sound_layout.addWidget(self.alert_sound_edit)
        sound_layout.addWidget(self.sound_browse_button)
        
        self.behavior_layout.addRow("Sound File:", sound_layout)
        
        self.behavior_group.setLayout(self.behavior_layout)
        
        # Add all groups to tab layout
        layout.addWidget(self.alert_on_group)
        layout.addWidget(self.appearance_group)
        layout.addWidget(self.behavior_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab
    
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
        
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout()
        
        # Start at boot
        self.start_boot_check = QCheckBox()
        startup_layout.addRow("Start on System Boot:", self.start_boot_check)
        
        # Start minimized
        self.start_minimized_check = QCheckBox()
        startup_layout.addRow("Start Minimized:", self.start_minimized_check)
        
        startup_group.setLayout(startup_layout)
        
        # UI settings group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()
        
        # Always on top
        self.always_top_check = QCheckBox()
        ui_layout.addRow("Always on Top:", self.always_top_check)
        
        # Minimize to tray
        self.minimize_tray_check = QCheckBox()
        ui_layout.addRow("Minimize to System Tray:", self.minimize_tray_check)
        
        ui_group.setLayout(ui_layout)

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
        layout.addWidget(startup_group)
        layout.addWidget(ui_group)
        layout.addWidget(snapshot_group)
        layout.addStretch(1)
        
        tab.setLayout(layout)
        return tab
    
    def _load_settings(self):
        """Load settings from configuration manager into UI components."""
        # Detection tab
        detector_type = self.config_manager.get("detector_type", "yunet")
        self.model_type_combo.setCurrentText(detector_type)
        self._on_model_type_changed(detector_type)  # Populate model path combo
        
        model_path = self.config_manager.get("model_path", "")
        index = self.model_path_combo.findText(model_path)
        if index >= 0:
            self.model_path_combo.setCurrentIndex(index)
        
        self.confidence_spin.setValue(self.config_manager.get("confidence_threshold", 0.5))
        self.face_threshold_spin.setValue(self.config_manager.get("face_threshold", 1))
        self.debounce_spin.setValue(self.config_manager.get("debounce_time", 1.0))
        self.detection_delay_spin.setValue(self.config_manager.get("detection_delay", 0.2))
        #self.show_detection_check.setChecked(self.config_manager.get("show_detection_visualization", True))
        self.privacy_mode_check.setChecked(self.config_manager.get("privacy_mode", False))
        
        # Alert tab
        self.alert_text_edit.setText(self.config_manager.get("alert_text", "EYES OFF!!!"))
        self.alert_color_button.set_color(self.config_manager.get("alert_color", (0, 0, 255)))
        self.alert_opacity_slider.setValue(int(self.config_manager.get("alert_opacity", 0.8) * 100))
        
        alert_size = self.config_manager.get("alert_size", (600, 300))
        self.alert_width_spin.setValue(alert_size[0])
        self.alert_height_spin.setValue(alert_size[1])
        
        self.alert_position_combo.setCurrentText(self.config_manager.get("alert_position", "center"))
        self.animations_check.setChecked(self.config_manager.get("enable_animations", True))
        self.fullscreen_check.setChecked(self.config_manager.get("fullscreen_mode", False))
        
        alert_duration = self.config_manager.get("alert_duration", None)
        if alert_duration is not None:
            self.auto_dismiss_check.setChecked(True)
            self.alert_duration_spin.setValue(alert_duration)
            self.alert_duration_spin.setEnabled(True)
        else:
            self.auto_dismiss_check.setChecked(False)
            self.alert_duration_spin.setEnabled(False)
        
        alert_sound_enabled = self.config_manager.get("alert_sound_enabled", False)
        self.alert_sound_check.setChecked(alert_sound_enabled)
        self.alert_sound_edit.setEnabled(alert_sound_enabled)
        self.sound_browse_button.setEnabled(alert_sound_enabled)
        self.alert_sound_edit.setText(self.config_manager.get("alert_sound_file", ""))
        
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
        
        # Set native notifications to true by default for the hybrid approach
        self.native_notifications_check.setChecked(True)
        self.config_manager.set("use_native_notifications", True)
        
        # App tab
        self.start_boot_check.setChecked(self.config_manager.get("start_on_boot", False))
        self.start_minimized_check.setChecked(self.config_manager.get("start_minimized", False))
        self.always_top_check.setChecked(self.config_manager.get("always_on_top", False))
        self.minimize_tray_check.setChecked(self.config_manager.get("minimize_to_tray", True))
        # Add setting for getting the snapshot path
        self.path_edit.setText(self.config_manager.get("snapshot_path", ""))
    
    def _on_model_type_changed(self, model_type: str):
        """
        Handle model type change.
        
        Args:
            model_type: New model type
        """
        # Clear and repopulate model path combo
        self.model_path_combo.clear()
        
        if model_type in self.available_models and self.available_models[model_type]:
            self.model_path_combo.addItems(self.available_models[model_type])
        
        # Enable apply button as settings have changed
        self.apply_button.setEnabled(True)
    
    def _on_auto_dismiss_toggled(self, checked: bool):
        """
        Handle auto-dismiss checkbox toggle.
        
        Args:
            checked: New checkbox state
        """
        self.alert_duration_spin.setEnabled(checked)
    
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
    
    def _on_reset_clicked(self):
        """Handle reset button click."""
        # Reset configuration to defaults
        self.config_manager.reset_to_defaults()
        
        # Reload settings
        self._load_settings()
        
        # Emit signal to notify of changes
        self.settings_changed.emit(self.config_manager.get_all())
    
    def _on_test_alert_clicked(self):
        """Handle test alert button click."""
        # Emit signal to request test alert
        self.test_alert_requested.emit()

    def _on_alert_toggle_clicked(self, checked: bool):
        """Activate alert settings if we toggle the alert on"""
        self.appearance_group.setEnabled(checked)
        self.behavior_group.setEnabled(checked)
    
    def _on_apply_clicked(self):
        """Handle apply button click."""
        # Gather all settings from UI
        settings = {}
        
        # Detection tab
        settings["detector_type"] = self.model_type_combo.currentText()
        settings["model_path"] = self.model_path_combo.currentText()
        settings["confidence_threshold"] = self.confidence_spin.value()
        settings["face_threshold"] = self.face_threshold_spin.value()
        settings["debounce_time"] = self.debounce_spin.value()
        settings["detection_delay"] = self.detection_delay_spin.value()
        #settings["show_detection_visualization"] = self.show_detection_check.isChecked()
        settings["privacy_mode"] = self.privacy_mode_check.isChecked()
        
        # Alert tab
        settings["alert_on"] = self.alert_on_check.isChecked()
        settings["alert_text"] = self.alert_text_edit.text()
        settings["alert_color"] = self.alert_color_button.bgr_color
        settings["alert_opacity"] = self.alert_opacity_slider.value() / 100.0
        settings["alert_size"] = (self.alert_width_spin.value(), self.alert_height_spin.value())
        settings["alert_position"] = self.alert_position_combo.currentText()
        settings["enable_animations"] = self.animations_check.isChecked()
        settings["fullscreen_mode"] = self.fullscreen_check.isChecked()
        settings["use_native_notifications"] = self.native_notifications_check.isChecked()
        
        if self.auto_dismiss_check.isChecked():
            settings["alert_duration"] = self.alert_duration_spin.value()
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
        
        # Update configuration
        self.config_manager.update(settings)
        self.config_manager.save_config()
        
        # Emit signal to notify of changes
        self.settings_changed.emit(settings)