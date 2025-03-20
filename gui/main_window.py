from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QSplitter, QAction, QMenu, QStatusBar, QMessageBox,
                           QSystemTrayIcon, QStyle, QApplication)
from PyQt5.QtCore import Qt, QTimer, QSettings, pyqtSlot
from PyQt5.QtGui import QIcon, QCloseEvent

import os
import sys
import time
from typing import Dict, Any, Optional

from gui.webcam_view import WebcamView
from gui.settings import SettingsPanel
from gui.alert import AlertDialog
from utils.config import ConfigManager
from core.webcam import WebcamManager
from core.detector import FaceDetector
from core.manager import DetectionManagerThread


class MainWindow(QMainWindow):
    """
    Main window for the EyesOff application.
    Integrates all UI components and connects them to the core functionality.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Configuration
        self.config_manager = ConfigManager()
        
        # Core components
        self.webcam_manager = None
        self.face_detector = None
        self.detection_thread = None
        
        # Frame processing timer
        self.frame_timer = None
        
        # UI components
        self.webcam_view = None
        self.settings_panel = None
        self.alert_dialog = None
        self.tray_icon = None
        
        # State variables
        self.is_monitoring = False
        self.last_error_time = 0
        self.error_debounce = 1.0  # seconds
        
        # Initialize UI and components
        self._init_ui()
        self._init_components()
        
        # Apply settings
        self._apply_settings(self.config_manager.get_all())
        
        # Auto-start if configured
        if not self.config_manager.get("start_minimized", False):
            self._start_monitoring()
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Set window properties
        self.setWindowTitle("EyesOff Privacy Monitor")

        # Disable full-screen capability
        self.setWindowFlags((self.windowFlags() & ~Qt.WindowFullscreenButtonHint & ~Qt.WindowMaximizeButtonHint) | Qt.CustomizeWindowHint)

        self.setMinimumSize(1000, 600)
        
        # Create central widget
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels - splitter is the panels
        # for settings and the webcam view
        # splitter = QSplitter(Qt.Horizontal)
        
        # Create webcam view
        self.webcam_view = WebcamView()
        self.webcam_view.monitoring_toggled.connect(self._on_monitoring_toggled)
        
        # Create settings panel
        self.settings_panel = SettingsPanel(self.config_manager)
        self.settings_panel.settings_changed.connect(self._apply_settings)
        self.settings_panel.test_alert_requested.connect(self._show_test_alert)

        # Add widgets to horizontal layout
        main_layout.addWidget(self.webcam_view, 7)  # 70% width
        main_layout.addWidget(self.settings_panel, 3)  # 30% width
        
        # Set layout to central widget
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Create menu bar
        self._create_menus()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("EyesOff Privacy Monitor")
        
        # Create tray icon
        self._create_tray_icon()
        
        # Set window position
        self._center_window()
    
    def _create_menus(self):
        """Create application menus."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # Start/stop monitoring action
        self.start_action = QAction("Start Monitoring", self)
        self.start_action.triggered.connect(self._start_monitoring)
        file_menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Monitoring", self)
        self.stop_action.triggered.connect(self._stop_monitoring)
        self.stop_action.setEnabled(False)
        file_menu.addAction(self.stop_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = self.menuBar().addMenu("&Settings")
        
        # Test alert action
        test_alert_action = QAction("Test Alert", self)
        test_alert_action.triggered.connect(self._show_test_alert)
        settings_menu.addAction(test_alert_action)
        
        settings_menu.addSeparator()
        
        # Reset settings action
        reset_settings_action = QAction("Reset to Defaults", self)
        reset_settings_action.triggered.connect(self._reset_settings)
        settings_menu.addAction(reset_settings_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tray_icon(self):
        """Create system tray icon."""
        # Create QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use a standard icon
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Add actions to tray menu
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        start_action = QAction("Start Monitoring", self)
        start_action.triggered.connect(self._start_monitoring)
        tray_menu.addAction(start_action)
        
        stop_action = QAction("Stop Monitoring", self)
        stop_action.triggered.connect(self._stop_monitoring)
        tray_menu.addAction(stop_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._exit_app)
        tray_menu.addAction(exit_action)
        
        # Set the tray menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Connect activated signal
        self.tray_icon.activated.connect(self._tray_icon_activated)
        
        # Show the tray icon
        self.tray_icon.show()
    
    def _center_window(self):
        """Center the window on the screen."""
        screen_geometry = QApplication.desktop().screenGeometry()
        window_geometry = self.geometry()
        
        self.move(
            int((screen_geometry.width() - window_geometry.width()) / 2),
            int((screen_geometry.height() - window_geometry.height()) / 2)
        )
    
    def _init_components(self):
        """Initialize the core components."""
        try:
            # Create webcam manager - We get the frame_width and height from settings
            self.webcam_manager = WebcamManager(
                camera_id=self.config_manager.get("camera_id", 0),
                frame_width=self.config_manager.get("frame_width", 640),
                frame_height=self.config_manager.get("frame_height", 480)
            )
            
            # Connect signals
            self.webcam_manager.frame_ready.connect(self.webcam_view.update_frame)
            self.webcam_manager.error_occurred.connect(self._handle_error)
            
            # Create face detector
            self.face_detector = FaceDetector(
                detector_type=self.config_manager.get("detector_type", "yunet"),
                model_path=self.config_manager.get("model_path", ""),
                confidence_threshold=self.config_manager.get("confidence_threshold", 0.5)
            )
            
            # Connect signals
            self.face_detector.signals.detection_ready.connect(self.webcam_view.update_detection)
            self.face_detector.signals.error_occurred.connect(self._handle_error)
            
            # Create detection manager thread
            self.detection_thread = DetectionManagerThread(self.config_manager.get_all())
            
            # Connect signals
            self.detection_thread.signals.alert_state_changed.connect(self.webcam_view.update_alert_state)
            self.detection_thread.signals.error_occurred.connect(self._handle_error)
            self.detection_thread.signals.stats_updated.connect(self._handle_stats_update)
            self.detection_thread.signals.show_alert.connect(self._on_show_alert)
            self.detection_thread.signals.dismiss_alert.connect(self._on_dismiss_alert)
            
            # Create frame processing timer
            self.frame_timer = QTimer(self)
            self.frame_timer.timeout.connect(self._process_frame)
            
            # Create alert dialog
            self._create_alert_dialog()
            
        except Exception as e:
            self._show_error_message(f"Error initializing components: {e}")
    
    def _create_alert_dialog(self):
        """Create the alert dialog."""
        self.alert_dialog = AlertDialog(
            self,
            alert_text=self.config_manager.get("alert_text", "EYES OFF!!!"),
            alert_color=self.config_manager.get("alert_color", (0, 0, 255)),
            alert_opacity=self.config_manager.get("alert_opacity", 0.8),
            alert_size=self.config_manager.get("alert_size", (600, 300)),
            alert_position=self.config_manager.get("alert_position", "center"),
            enable_animations=self.config_manager.get("enable_animations", True),
            alert_duration=self.config_manager.get("alert_duration", None),
            alert_sound_enabled=self.config_manager.get("alert_sound_enabled", False),
            alert_sound_file=self.config_manager.get("alert_sound_file", ""),
            fullscreen_mode=self.config_manager.get("fullscreen_mode", False),
            use_native_notifications=self.config_manager.get("use_native_notifications", False),
            on_notification_clicked=self.show
        )
    
    def _start_monitoring(self):
        """Start the monitoring process."""
        if self.is_monitoring:
            return
            
        try:
            # Start webcam
            if not self.webcam_manager.start():
                self._show_error_message("Failed to start webcam")
                return
            
            # Start detection thread
            self.detection_thread.start()
            
            # Start frame processing timer
            self.frame_timer.start(30)  # Process frames every 30ms (~33 fps)
            
            # Update state and UI
            self.is_monitoring = True
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            
            # Update webcam view state
            if self.webcam_view:
                self.webcam_view.set_monitoring_state(True)
            
            # Update status bar
            self.statusBar.showMessage("Monitoring active")
            
            # Update tray icon tooltip
            if self.tray_icon:
                self.tray_icon.setToolTip("EyesOff - Monitoring Active")
            
        except Exception as e:
            self._show_error_message(f"Error starting monitoring: {e}")
    
    def _stop_monitoring(self):
        """Stop the monitoring process."""
        if not self.is_monitoring:
            return
            
        try:
            # Explicitly dismiss any visible alerts first
            if self.alert_dialog and self.alert_dialog.isVisible():
                self.alert_dialog.close()

            # Stop frame timer
            if self.frame_timer and self.frame_timer.isActive():
                self.frame_timer.stop()
            
            # Stop detection thread
            if self.detection_thread and self.detection_thread.isRunning():
                self.detection_thread.stop()
                self.detection_thread.wait()  # Wait for thread to finish
            
            # Stop webcam
            if self.webcam_manager:
                self.webcam_manager.stop()
            
            # Clear webcam view
            if self.webcam_view:
                self.webcam_view.clear_display()
            
            # Update state and UI
            self.is_monitoring = False
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            
            # Update webcam view state
            if self.webcam_view:
                self.webcam_view.set_monitoring_state(False)
            
            # Update status bar
            self.statusBar.showMessage("Monitoring stopped")
            
            # Update tray icon tooltip
            if self.tray_icon:
                self.tray_icon.setToolTip("EyesOff - Monitoring Stopped")
            
        except Exception as e:
            self._show_error_message(f"Error stopping monitoring: {e}")
    
    def _process_frame(self):
        """Process a webcam frame."""
        try:
            # Read frame from webcam
            success, frame = self.webcam_manager.read_frame()
            if not success or frame is None:
                return
            
            # Detect faces
            num_faces, bboxes, _ = self.face_detector.detect(frame)
            
            # Update detection manager
            self.detection_thread.update_face_count(num_faces)
            
        except Exception as e:
            self._handle_error(f"Error processing frame: {e}")
    
    def _apply_settings(self, settings: Dict[str, Any]):
        """
        Apply new settings to all components.
        
        Args:
            settings: Dictionary of settings to apply
        """
        try:
            # Update webcam settings
            if self.webcam_manager:
                # Check if camera changed
                if 'camera_id' in settings:
                    self.webcam_manager.set_camera(settings['camera_id'])
                
                # Check if resolution changed
                if 'frame_width' in settings and 'frame_height' in settings:
                    self.webcam_manager.set_resolution(settings['frame_width'], settings['frame_height'])
            
            # Update detector settings
            if self.face_detector:
                detector_settings = {k: v for k, v in settings.items() 
                                   if k in ('detector_type', 'model_path', 'confidence_threshold')}
                if detector_settings:
                    self.face_detector.update_settings(detector_settings)
            
            # Update detection thread settings
            if self.detection_thread:
                self.detection_thread.update_settings(settings)
            
            # Update webcam view settings
            if self.webcam_view:
                # Update face threshold
                if 'face_threshold' in settings:
                    self.webcam_view.face_threshold = settings['face_threshold']
                    
                # Update privacy mode if present
                if 'privacy_mode' in settings:
                    self.webcam_view.set_privacy_mode(settings['privacy_mode'])
                    
                # Refresh display
                if hasattr(self.webcam_view, 'detection_result') and self.webcam_view.detection_result is not None:
                    self.webcam_view._update_display()
            
            # Update alert dialog settings
            if self.alert_dialog:
                alert_settings = {}
                if 'alert_text' in settings:
                    alert_settings['alert_text'] = settings['alert_text']
                if 'alert_color' in settings:
                    alert_settings['alert_color'] = settings['alert_color']
                if 'alert_opacity' in settings:
                    alert_settings['alert_opacity'] = settings['alert_opacity']
                if 'alert_size' in settings:
                    alert_settings['alert_size'] = settings['alert_size']
                if 'alert_position' in settings:
                    alert_settings['alert_position'] = settings['alert_position']
                if 'enable_animations' in settings:
                    alert_settings['enable_animations'] = settings['enable_animations']
                if 'alert_duration' in settings:
                    alert_settings['alert_duration'] = settings['alert_duration']
                if 'alert_sound_enabled' in settings:
                    alert_settings['alert_sound_enabled'] = settings['alert_sound_enabled']
                if 'alert_sound_file' in settings:
                    alert_settings['alert_sound_file'] = settings['alert_sound_file']
                if 'fullscreen_mode' in settings:
                    alert_settings['fullscreen_mode'] = settings['fullscreen_mode']
                if 'use_native_notifications' in settings:
                    alert_settings['use_native_notifications'] = settings['use_native_notifications']
                    
                if alert_settings:
                    self.alert_dialog.update_settings(**alert_settings)
            
            # Apply always on top setting
            if 'always_on_top' in settings:
                self._set_always_on_top(settings['always_on_top'])
            
            # Save settings to config
            self.config_manager.save_config()
            
        except Exception as e:
            self._show_error_message(f"Error applying settings: {e}")
    
    def _set_always_on_top(self, always_on_top: bool):
        """
        Set the window to always stay on top.
        
        Args:
            always_on_top: Whether the window should stay on top
        """
        flags = self.windowFlags()
        if always_on_top:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()
    
    
    def _reset_settings(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset configuration
            self.config_manager.reset_to_defaults()
            
            # Reload settings in UI
            if self.settings_panel:
                self.settings_panel._load_settings()
            
            # Apply reset settings
            self._apply_settings(self.config_manager.get_all())
            
            # Show confirmation
            self.statusBar.showMessage("Settings reset to defaults", 3000)
    
    def _show_test_alert(self):
        """Show a test alert."""
        if self.alert_dialog:
            self.alert_dialog.test_alert()
    
    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About EyesOff",
            "EyesOff Privacy Monitor v1.0.0\n\n"
            "A privacy protection application that monitors your webcam "
            "for unauthorized viewers and displays an alert when someone "
            "else is looking at your screen."
        )
    
    def _on_privacy_toggled(self, enabled: bool):
        """
        Handle privacy mode toggle from webcam view.
        
        Args:
            enabled: Whether privacy mode is enabled
        """
        # Update configuration
        self.config_manager.set("privacy_mode", enabled)
        
        # Update status bar
        if enabled:
            self.statusBar.showMessage("Privacy mode enabled", 3000)
        else:
            self.statusBar.showMessage("Privacy mode disabled", 3000)

    def _on_show_alert(self):
        """Handle signal to show the alert dialog."""
        # Check if alert is toggled on
        alert_on = self.config_manager.get("alert_on")
        print(f"IS ALERT ON: {alert_on}")

        if not alert_on:
            # If alert is turned off, simply show native notification
            self.alert_dialog._show_native_notification()

            # Log for debugging
            print("DEBUG: Showing notification (alert is turned off)")
            print('---' * 25)
        else:
            # Alert is on - show the window alert and bring main window to foreground
            if not self.alert_dialog:
                return

            # First, activate the main application window to bring it to the foreground
            self.activateWindow()  # This makes your main window active
            self.raise_()  # This raises it to the top

            # If existing popup is visible, close it first to prevent duplicates
            if self.alert_dialog.isVisible():
                self.alert_dialog.close()

            # Check fullscreen setting
            fullscreen_setting = self.config_manager.get("fullscreen_mode", False)

            # Make sure to use correct fullscreen setting
            if self.alert_dialog.fullscreen_mode != fullscreen_setting:
                # Close and recreate alert dialog with new setting
                self.alert_dialog.close()
                self._create_alert_dialog()

            # Show the alert window
            self.alert_dialog.show()

            # Log for debugging
            print(f"DEBUG: Showing {'fullscreen' if self.alert_dialog.fullscreen_mode else 'regular'} popup alert")
            print('---' * 25)
            
    def _on_dismiss_alert(self):
        """Handle signal to dismiss the alert dialog."""
        if self.alert_dialog and self.alert_dialog.isVisible():
            self.alert_dialog.close()
            
    def _on_monitoring_toggled(self, enable: bool):
        """
        Handle monitoring toggle from webcam view.
        
        Args:
            enable: Whether to enable monitoring
        """
        if enable and not self.is_monitoring:
            self._start_monitoring()
        elif not enable and self.is_monitoring:
            self._stop_monitoring()
    
    def _handle_error(self, error_message: str):
        """
        Handle error messages from components.
        
        Args:
            error_message: Error message
        """
        # Apply debouncing to prevent error message spam
        current_time = time.time()
        if current_time - self.last_error_time > self.error_debounce:
            self.last_error_time = current_time
            self.statusBar.showMessage(f"Error: {error_message}", 5000)
            print(f"Error: {error_message}")
    
    def _handle_stats_update(self, stats: Dict[str, Any]):
        """
        Handle detection statistics updates.
        
        Args:
            stats: Dictionary of detection statistics
        """
        # Update status bar with simplified statistics summary
        if 'alert_count' in stats:
            elapsed_time = 0
            if stats.get('session_start_time'):
                elapsed_time = time.time() - stats['session_start_time']
                
            status = f"Alerts: {stats['alert_count']} | " \
                     f"Session: {int(elapsed_time / 60)}m {int(elapsed_time % 60)}s"
                     
            self.statusBar.showMessage(status)
    
    def _show_error_message(self, message: str):
        """
        Show an error message box.
        
        Args:
            message: Error message
        """
        QMessageBox.critical(self, "Error", message)
    
    def _tray_icon_activated(self, reason):
        """
        Handle tray icon activation.
        
        Args:
            reason: Activation reason
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
    
    def _exit_app(self):
        """Exit the application."""
        self.close()
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        if self.tray_icon and self.tray_icon.isVisible() and self.config_manager.get("minimize_to_tray", True):
            # Ask if the user wants to minimize to tray or exit
            reply = QMessageBox.question(
                self,
                "EyesOff",
                "Do you want to minimize to the system tray?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Minimize to tray
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "EyesOff",
                    "EyesOff is still running in the background.",
                    QSystemTrayIcon.Information,
                    2000
                )
                return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        
        # Stop monitoring if running
        if self.is_monitoring:
            self._stop_monitoring()
        
        # Save window geometry
        self.config_manager.set("window_geometry", self.saveGeometry().toBase64().data().decode())
        
        # Accept the close event
        event.accept()
        
        # Quit the application
        QApplication.quit()
    
    def showEvent(self, event):
        """
        Handle window show event.
        
        Args:
            event: Show event
        """
        super().showEvent(event)
        
        # Try to restore window geometry
        geometry_data = self.config_manager.get("window_geometry")
        if geometry_data:
            try:
                from PyQt5.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromBase64(geometry_data.encode()))
            except:
                self._center_window()
        else:
            self._center_window()

        # Resize the webcam view to fit
        # Add a small delay to ensure everything is properly laid out
        QTimer.singleShot(100, self._resize_webcam_view)

    def _resize_webcam_view(self):
        """Resize the webcam view to fit the available space in the splitter."""
        if not self.webcam_view or not self.webcam_manager:
            return

        # Get the current size of the webcam view's container in the splitter
        container_width = self.webcam_view.width()
        container_height = self.webcam_view.height()

        # Get the current display resolution
        display_width = self.webcam_manager.frame_width
        display_height = self.webcam_manager.frame_height

        # Calculate aspect ratio of the webcam feed
        aspect_ratio = display_width / display_height

        # Set maximum dimensions to prevent excessive growth
        max_width = min(1600, container_width - 40)  # Max 1600px or container width - 40px
        max_height = min(900, container_height - 40)  # Max 900px or container height - 40px

        # Set a fixed size for the webcam label that maintains aspect ratio
        # and fits within the container and maximum limits
        if container_width / container_height > aspect_ratio:
            # Container is wider than needed - height is the limiting factor
            new_height = min(max_height, container_height - 40)  # Account for padding/margins
            new_width = int(new_height * aspect_ratio)

            # Check if width exceeds max_width
            if new_width > max_width:
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
        else:
            # Container is taller than needed - width is the limiting factor
            new_width = min(max_width, container_width - 40)  # Account for padding/margins
            new_height = int(new_width / aspect_ratio)

            # Check if height exceeds max_height
            if new_height > max_height:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)

        # Update the webcam view's label size
        self.webcam_view.webcam_label.setFixedSize(new_width, new_height)

        print(f"Resized webcam view to {new_width}x{new_height} (container: {container_width}x{container_height})")
