import os
import sys
import time
from typing import Dict, Any, Optional

from PyQt5.QtCore import Qt, QTimer, QSettings, pyqtSlot
from PyQt5.QtGui import QIcon, QCloseEvent, QKeySequence
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
							 QSplitter, QAction, QMenu, QStatusBar, QMessageBox,
							 QSystemTrayIcon, QStyle, QApplication)

from core.detector import FaceDetector
from core.manager import DetectionManagerThread
from core.webcam import WebcamManager
from core.update_checker import UpdateManager
from gui.alert import AlertDialog
from gui.preferences_window import PreferencesWindow
from gui.webcam_view import WebcamView
from gui.update_view import UpdateView
from gui.help.walkthrough import WalkthroughDialog
from utils.config import ConfigManager
from utils.platform import get_platform_manager


class MainWindow(QMainWindow):
    """
    Main window for the EyesOff application.
    Integrates all UI components and connects them to the core functionality.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Get platform manager (singleton)
        self.platform_manager = get_platform_manager()
        
        # Configuration
        self.config_manager = ConfigManager()
        
        # Core components
        self.webcam_manager = None
        self.face_detector = None
        self.detection_thread = None
        self.update_manager = None
        
        # Frame processing timer
        self.frame_timer = None
        
        # UI components
        self.webcam_view = None
        self.preferences_window = None
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
        
        # Check for first run
        self._check_first_run()
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Set window properties
        self.setWindowTitle("EyesOff Privacy Monitor")

        # Enable maximize and fullscreen capabilities for better webcam display
        self.setWindowFlags(self.windowFlags() | Qt.WindowFullscreenButtonHint | Qt.WindowMaximizeButtonHint)

        self.setMinimumSize(640, 480)  # More flexible minimum size for any screen
        
        # Create central widget
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create webcam view
        self.webcam_view = WebcamView()
        self.webcam_view.monitoring_toggled.connect(self._on_monitoring_toggled)

        # Add widgets to horizontal layout
        main_layout.addWidget(self.webcam_view)
        
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

        if sys.platform != "darwin":
            file_menu.addSeparator()
            # Exit action
            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
        
        # Edit menu for macOS convention
        edit_menu = self.menuBar().addMenu("&Edit")

        # Settings... action TODO - currently its called Preferences... i want to change it to Settings... but PyQT seems to rename it preferences on its own
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(self._show_settings)

        edit_menu.addAction(settings_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # Walkthrough action
        walkthrough_action = QAction("Show Tutorial", self)
        walkthrough_action.triggered.connect(self._show_walkthrough)
        help_menu.addAction(walkthrough_action)

        help_menu.addSeparator()

        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tray_icon(self):
        """Create system tray icon."""
        # Create QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use a standard icon
        self.tray_icon.setIcon(QIcon('gui/resources/icons/eyesoff_refined_logo.png'))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Add actions to tray menu
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._show_settings)
        tray_menu.addAction(settings_action)
        
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

    def _show_settings(self):
        if self.preferences_window is None:
            self.preferences_window = PreferencesWindow(self.config_manager, self)
            self.preferences_window.preferences_changed.connect(self._apply_settings)

        self.preferences_window.show()
        self.preferences_window.raise_()
        self.preferences_window.activateWindow()

    
    def _init_components(self):
        """Initialize the core components."""
        try:
            # Create webcam manager - simplified, no resolution parameters
            self.webcam_manager = WebcamManager(
                camera_id=self.config_manager.get("camera_id", 0)
            )
            
            # Connect signals
            self.webcam_manager.frame_ready.connect(self.webcam_view.update_frame)
            self.webcam_manager.error_occurred.connect(self._handle_error)
            
            # Create face detector
            self.face_detector = FaceDetector(
                detector_type=self.config_manager.get("detector_type", "yunet"),
                model_path=self.config_manager.get("model_path", ""),
                confidence_threshold=self.config_manager.get("confidence_threshold", 0.5),
                gaze_threshold=self.config_manager.get("gaze_threshold", 0.3)
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
            # Connect a signal to take a screenshot of screen when we show alert
            self.detection_thread.signals.show_alert.connect(self._capture_webcam_on_alert)

            #Init Update Manager
            self.update_manager = UpdateManager(self)
            QTimer.singleShot(3000, self.update_manager.start)

            # Connect update signals
            self.update_manager.thread.update_available.connect(self._show_update_dialog)

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
            launch_app_enabled=self.config_manager.get("launch_app_enabled", False),
            launch_app_path=self.config_manager.get("launch_app_path", ""),
            on_notification_clicked=self.show
        )

        # Connect the user dismissal signal from the alert_dialog
        self.alert_dialog.signals.user_dismiss_alert.connect(self._on_dismiss_alert)
    
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
            self.detection_thread.start()  # .start() is an inherited method from the QThread class, it calls the run function in a Qthread
            
            # Start frame processing timer
            # TODO: increase this? https://chatgpt.com/share/681f55ed-8ab4-800d-99f4-800a6a2c6abd
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
            num_faces, bboxes, _, num_looking = self.face_detector.detect(frame)
            
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

                if 'snapshot_path' in settings:
                    print(settings['snapshot_path'])
                    self.webcam_view.dir_to_save = settings['snapshot_path']
            
            # Update alert dialog settings
            if self.alert_dialog:
                alert_settings = {}
                if 'alert_on' in settings:
                    alert_settings['alert_on'] = settings['alert_on']
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
                if 'launch_app_enabled' in settings:
                    alert_settings['launch_app_enabled'] = settings['launch_app_enabled']
                if 'launch_app_path' in settings:
                    alert_settings['launch_app_path'] = settings['launch_app_path']
                    
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
        # Use platform manager to set window flags
        self.platform_manager.window_manager.set_window_flags(
            self, 
            always_on_top=always_on_top, 
            frameless=False
        )
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
    
    def _show_walkthrough(self):
        """Show the interactive walkthrough."""
        walkthrough = WalkthroughDialog(self)
        walkthrough.walkthrough_finished.connect(self._on_walkthrough_finished)
        walkthrough.exec_()

    def _on_walkthrough_finished(self):
        """Handle walkthrough completion."""
        self.config_manager.set("first_run", False)
        self.config_manager.set("walkthrough_completed", True)
        self.config_manager.save_config()
        
    def _check_first_run(self):
        """Check if this is the first run and show walkthrough."""
        if self.config_manager.get("first_run", True):
            # Show walkthrough after a short delay to ensure window is ready
            QTimer.singleShot(500, self._show_walkthrough)
    
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

    def _capture_webcam_on_alert(self):
        """
        Take a capture of the webcam when we show the alert for user review later
        """
        self.webcam_view.on_snapshot_clicked()

    def _on_show_alert(self):
        """Handle signal to show the alert dialog."""
        # Check if alert is toggled on
        alert_on = self.config_manager.get("alert_on")

        # Check if app launch is enabled
        launch_app_enabled = self.config_manager.get("launch_app_enabled", False)
        launch_app_path = self.config_manager.get("launch_app_path", "")

        if launch_app_enabled and launch_app_path:
            # Use notification and launch app
            if self.alert_dialog:
                self.alert_dialog._show_native_notification()
                QTimer.singleShot(200, self.alert_dialog._launch_external_app)

            # Show the alert indicator in the UI
            if self.detection_thread and self.detection_thread.detection_manager:
                self.detection_thread.detection_manager.is_alert_showing = True
                self.webcam_view.update_alert_state(True)

            print("DEBUG: Launching app and showing notification")
        elif not alert_on:
            # If alert is turned off, simply show native notification
            if self.alert_dialog:
                self.alert_dialog._show_native_notification()

            # Show the alert indicator in the UI
            if self.detection_thread and self.detection_thread.detection_manager:
                self.detection_thread.detection_manager.is_alert_showing = True
                self.webcam_view.update_alert_state(True)

            # Set a timer to auto-dismiss after a short period
            QTimer.singleShot(500, self._auto_dismiss_notification_alert)

            print("DEBUG: Showing notification (alert is turned off)")
        else:
            # Show alert dialog
            if not self.alert_dialog:
                return

            # First, activate the main application window
            self.activateWindow()
            self.raise_()

            # Close existing popup if visible
            if self.alert_dialog.isVisible():
                self.alert_dialog.close()

            # Ensure alert dialog has latest settings
            self._refresh_alert_dialog_visual_settings()

            # Show the alert window
            self.alert_dialog.show()

            print(f"DEBUG: Showing popup alert")

    def _refresh_alert_dialog_visual_settings(self):
        """Refresh the alert dialog with current settings."""
        print("DEBUG: Refreshing alert visuals")
        if not self.alert_dialog:
            return

        # Apply current settings to ensure it's up to date
        settings = {
            "alert_color": self.config_manager.get("alert_color", (0, 0, 255)),
            "alert_opacity": self.config_manager.get("alert_opacity", 0.8),
            "alert_text": self.config_manager.get("alert_text", "EYES OFF!!!"),
            "fullscreen_mode": self.config_manager.get("fullscreen_mode", False),
            # Include other relevant settings
        }

        self.alert_dialog.update_settings(**settings)
            
    def _on_dismiss_alert(self):
        """Handle signal to dismiss the alert dialog."""
        if self.alert_dialog and self.alert_dialog.isVisible():
            self.alert_dialog.close()

        # Reset the detection manager state
        # TODO - Now we handle the detection_manager.is_alert_showing state in two locations, we should improve this
        if self.detection_thread and self.detection_thread.detection_manager:
            self.detection_thread.handle_user_dismissal()
            self.statusBar.showMessage("Alert dismissed", 2000)

    def _auto_dismiss_notification_alert(self):
        """Auto-dismiss alert state after notification is shown"""
        if self.detection_thread and self.detection_thread.detection_manager:
            self.detection_thread.detection_manager.is_alert_showing = False
            self.webcam_view.update_alert_state(False)  # Update UI
            print("DEBUG: Auto-dismissed notification alert")

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
        # Update status bar with simplified statistics
        status_parts = []
        
        # Alert count
        if 'alert_count' in stats:
            status_parts.append(f"Alerts: {stats['alert_count']}")
        
        # Session time
        if stats.get('session_start_time'):
            elapsed_time = time.time() - stats['session_start_time']
            status_parts.append(f"Session: {int(elapsed_time / 60)}m {int(elapsed_time % 60)}s")
        
        # Join all parts
        if status_parts:
            self.statusBar.showMessage(" | ".join(status_parts))
    
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
        """Resize the webcam view to fit the available space."""
        # Remove this method entirely - let the webcam view handle its own sizing dynamically
        pass

    # Update View
    def _show_update_dialog(self, new_version):
        """Show update dialog when a new version is available."""
        current_version = self.config_manager.get("app_version", "1.0.0")

        # Create the update view with version information
        self.update_view = UpdateView(self.update_manager, self, version_info=new_version)

        # Connect to update signals
        self.update_view.update_accepted.connect(self._handle_update_accepted)
        self.update_view.update_declined.connect(self._handle_update_declined)

        # Connect download progress signals
        self.update_manager.thread.download_progress.connect(self.update_view.update_progress)
        self.update_manager.thread.download_completed.connect(self.update_view.download_complete)
        
        # Connect verification signals
        self.update_manager.thread.verification_started.connect(self.update_view.show_verification_started)
        self.update_manager.thread.verification_success.connect(self.update_view.show_verification_success)
        self.update_manager.thread.verification_failed.connect(self.update_view.show_verification_failed)

        # Show the dialog
        self.update_view.exec_()

    def _handle_update_accepted(self):
        """Handle when user accepts the update."""

        self.update_manager.thread.start_download.emit()

        print('HANDLING UPDATE ACCEPTED BY USER')

    def _handle_update_declined(self):
        """Handle when user declines the update."""
        # Just log to status bar
        self.statusBar.showMessage("Update declined", 3000)
        self.update_manager.close_thread()
        print('HANDLING UPDATE DECLINE- CLOSING THREAD')