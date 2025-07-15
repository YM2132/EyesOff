from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QShortcut, QHBoxLayout, QPushButton

from gui.settings import SettingsPanel
from utils.config import ConfigManager


class PreferencesWindow(QDialog):
	"""
	Preferences window for the EyesOff application.
	Provides a separate window for application settings following macOS conventions.
	"""

	# Signal emitted when preferences are changed
	preferences_changed = pyqtSignal(dict)

	def __init__(self, config_manager: ConfigManager, parent=None):
		"""
		Initialize the preferences window.

		Args:
			config_manager: Configuration manager instance
			parent: Parent widget
		"""
		super().__init__(parent)
		self.config_manager = config_manager

		# Set window properties
		self.setWindowTitle("Settings")  # TODO - NAME the file settings_window
		self.setWindowModality(Qt.ApplicationModal)
		self.setMinimumSize(600, 800)

		# Initialize UI
		self._init_ui()

		# Set up keyboard shortcut for closing (Cmd+W on Mac)
		close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
		close_shortcut.activated.connect(self.close)

		# Load window geometry if saved
		self._restore_geometry()

	def _init_ui(self):
		"""Initialize the UI components."""
		# Main layout
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)

		# Create settings panel
		self.settings_panel = SettingsPanel(self.config_manager)

		# Connect settings changed signal
		self.settings_panel.settings_changed.connect(self._on_settings_changed)

		# Add settings panel to layout
		main_layout.addWidget(self.settings_panel)

		button_layout = QHBoxLayout()
		button_layout.setContentsMargins(10, 10, 10, 10)

		self.reset_button = QPushButton("Reset to Defaults", self)
		button_layout.addWidget(self.reset_button)

		button_layout.addStretch()

		self.cancel_button = QPushButton("Cancel")
		self.apply_button = QPushButton("Apply")
		self.ok_button = QPushButton("OK")

		self.apply_button.setEnabled(False)
		self.ok_button.setDefault(True)

		button_layout.addWidget(self.cancel_button)
		button_layout.addSpacing(6)
		button_layout.addWidget(self.apply_button)
		button_layout.addSpacing(6)
		button_layout.addWidget(self.ok_button)

		# Connect button signals
		self.reset_button.clicked.connect(self._on_reset_button_clicked)  # TODO -- make only reset upon apply
		self.cancel_button.clicked.connect(self._on_cancel_clicked)
		self.apply_button.clicked.connect(self._on_apply_clicked)
		self.ok_button.clicked.connect(self._on_ok_clicked)

		main_layout.addLayout(button_layout)

		self.setLayout(main_layout)

		# Store original settings for cancel functionality
		self.original_settings = self.config_manager.get_all().copy()

	def _on_reset_button_clicked(self):
		"""Handle reset button click."""
		# Use the settings panel's reset method
		new_settings = self.settings_panel.reset_to_defaults()

		# Update original settings to the new defaults
		self.original_settings = new_settings.copy()

		# Emit signal to update the main application
		self.preferences_changed.emit(self.original_settings)

		# Enable Apply button since we made changes
		self.apply_button.setEnabled(True)

	def _on_settings_changed(self, settings):
		"""
		Handle settings changes from the settings panel.

		Args:
			settings: Changed settings dictionary
		"""
		# Enable Apply button when settings change
		self.apply_button.setEnabled(True)

	def _on_ok_clicked(self):
		"""Handle OK button click."""
		# Apply settings and close
		self._apply_settings()
		self._save_geometry()
		self.accept()

	def _on_cancel_clicked(self):
		"""Handle Cancel button click."""
		# Restore original settings
		self.config_manager.update(self.original_settings)
		self.config_manager.save_config()

		# Emit signal to update the main application
		self.preferences_changed.emit(self.original_settings)

		self._save_geometry()
		self.reject()

	def _on_apply_clicked(self):
		"""Handle Apply button click."""
		self._apply_settings()

		# Update original settings to current state
		self.original_settings = self.config_manager.get_all().copy()

		# Disable Apply button after applying
		self.apply_button.setEnabled(False)

	def _apply_settings(self):
		"""Apply the current settings."""
		# Use the settings panel's apply method
		current_settings = self.settings_panel.apply_settings()

		# Emit signal to update the main application
		self.preferences_changed.emit(current_settings)

	def _save_geometry(self):
		"""Save window geometry to settings."""
		settings = QSettings("EyesOffApp", "EyesOff")
		settings.setValue("preferences_geometry", self.saveGeometry())

	def _restore_geometry(self):
		"""Restore window geometry from settings."""
		settings = QSettings("EyesOffApp", "EyesOff")
		geometry = settings.value("preferences_geometry")
		if geometry:
			self.restoreGeometry(geometry)
		else:
			# Center on parent if no saved geometry
			if self.parent():
				parent_rect = self.parent().geometry()
				x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
				y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
				self.move(x, y)

	def showEvent(self, event):
		"""Handle show event."""
		super().showEvent(event)

		# Reset original settings when showing
		self.original_settings = self.config_manager.get_all().copy()

		# Reload settings in the panel
		if hasattr(self.settings_panel, '_load_settings'):
			self.settings_panel._load_settings()

		# Disable Apply button initially
		self.apply_button.setEnabled(False)