import os
import sys
import time
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
							 QPushButton, QDialog, QSizePolicy, QSpacerItem,
							 QProgressBar, QMessageBox, QScrollArea, QFrame)

from utils.platform import get_platform_manager

class UpdateView(QDialog):
	"""
	Widget for displaying current app version, new app version.
	Also contains a yes and no box to ask the user whether they want to install the update.
	"""

	# Signals to communicate user's choice
	update_accepted = pyqtSignal()
	update_declined = pyqtSignal()

	def __init__(self, manager, parent=None, version_info=None):
		super().__init__(parent)
		self.manager = manager  # Store the update manager instance
		self.platform_manager = get_platform_manager()
		self.version_info = version_info or "(Unknown version)"
		self.file_path = None  # To store the downloaded file path
		
		# Track download state
		self.download_started = False
		self.download_completed = False
		self.download_failed = False
		
		# Set window properties
		self.setWindowTitle("Update Available")
		self.setModal(True)  # Make it a modal dialog
		self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
		
		# Fixed size for the dialog
		self.setFixedSize(500, 400)
		
		# Initialize UI
		self._init_ui()

		# Connect to download signals
		if self.manager and hasattr(self.manager, 'thread'):
			self.manager.thread.download_progress.connect(self.update_download_progress)
			self.manager.thread.download_completed.connect(self.download_complete)
			self.manager.thread.verification_started.connect(self.verification_started)
			self.manager.thread.verification_success.connect(self.verification_success)
			self.manager.thread.verification_failed.connect(self.verification_failed)

	def _init_ui(self):
		"""Initialize the UI components."""
		# Main layout
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(30, 30, 30, 30)
		main_layout.setSpacing(20)
		
		# Title
		title_label = QLabel("Update Available")
		title_label.setAlignment(Qt.AlignCenter)
		title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
		main_layout.addWidget(title_label)
		
		# Current version and new version info
		version_layout = QVBoxLayout()
		version_layout.setSpacing(10)
		
		current_version = self.manager.current_version if self.manager else "Unknown"
		current_label = QLabel(f"Current Version: {current_version}")
		current_label.setAlignment(Qt.AlignCenter)
		current_label.setStyleSheet("font-size: 14px;")
		version_layout.addWidget(current_label)
		
		new_label = QLabel(f"New Version: {self.version_info}")
		new_label.setAlignment(Qt.AlignCenter)
		new_label.setStyleSheet("font-size: 14px; color: #2E7D32; font-weight: bold;")
		version_layout.addWidget(new_label)
		
		main_layout.addLayout(version_layout)
		
		# Scrollable area for changelog/info
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		scroll_area.setMaximumHeight(150)
		
		# Message/info container
		self.message_container = QWidget()
		message_layout = QVBoxLayout(self.message_container)
		
		# Message label
		self.message_label = QLabel()
		self.message_label.setWordWrap(True)
		self.message_label.setAlignment(Qt.AlignTop)
		self.message_label.setStyleSheet("font-size: 13px; padding: 10px;")
		self.message_label.setText(
			"A new version of EyesOff is available!\n\n"
			"Would you like to download and install this update?\n\n"
			"The update process will:\n"
			"• Download the new version\n"
			"• Verify the download integrity\n"
			"• Guide you through installation"
		)
		message_layout.addWidget(self.message_label)
		
		scroll_area.setWidget(self.message_container)
		main_layout.addWidget(scroll_area)
		
		# Progress bar (hidden initially)
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		self.progress_bar.setStyleSheet("""
			QProgressBar {
				border: 1px solid #ccc;
				border-radius: 5px;
				text-align: center;
				height: 25px;
			}
			QProgressBar::chunk {
				background-color: #4CAF50;
				border-radius: 4px;
			}
		""")
		main_layout.addWidget(self.progress_bar)
		
		# Status label (hidden initially)
		self.status_label = QLabel()
		self.status_label.setVisible(False)
		self.status_label.setAlignment(Qt.AlignCenter)
		self.status_label.setStyleSheet("font-size: 12px; color: #666;")
		main_layout.addWidget(self.status_label)
		
		# Spacer
		main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
		
		# Button layout
		button_layout = QHBoxLayout()
		button_layout.setSpacing(20)
		
		# No button
		self.no_button = QPushButton("Later")
		self.no_button.setMinimumSize(120, 40)
		self.no_button.clicked.connect(self.on_no_clicked)
		button_layout.addWidget(self.no_button)
		
		button_layout.addStretch()
		
		# Yes button
		self.yes_button = QPushButton("Download Update")
		self.yes_button.setMinimumSize(120, 40)
		self.yes_button.setStyleSheet("""
			QPushButton {
				background-color: #4CAF50;
				color: white;
				border: none;
				border-radius: 5px;
				font-weight: bold;
			}
			QPushButton:hover {
				background-color: #45a049;
			}
			QPushButton:pressed {
				background-color: #3d8b40;
			}
		""")
		self.yes_button.clicked.connect(self.on_yes_clicked)
		button_layout.addWidget(self.yes_button)
		
		main_layout.addLayout(button_layout)
		
		# Set the layout
		self.setLayout(main_layout)

	def on_yes_clicked(self):
		"""Handle Yes button click - start download."""
		if not self.download_started:
			self.download_started = True
			
			# Update UI for download mode
			self.yes_button.setEnabled(False)
			self.yes_button.setText("Downloading...")
			self.no_button.setText("Cancel")
			
			# Show progress bar and status
			self.progress_bar.setVisible(True)
			self.status_label.setVisible(True)
			self.status_label.setText("Starting download...")
			
			# Update message
			self.message_label.setText(
				"Downloading update...\n\n"
				"Please wait while the update is downloaded and verified.\n"
				"This may take a few minutes depending on your connection speed."
			)
			
			# Emit the signal to trigger download
			self.update_accepted.emit()
			if self.manager and hasattr(self.manager, 'thread'):
				self.manager.thread.start_download.emit()
		elif self.download_completed and self.file_path:
			# If download is complete and Install button is clicked
			self.install_update()

	def on_no_clicked(self):
		"""Handle No/Cancel button click."""
		if self.download_started and not self.download_completed:
			# Ask for confirmation if download is in progress
			reply = QMessageBox.question(
				self, 
				'Cancel Download',
				'Are you sure you want to cancel the download?',
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No
			)
			
			if reply == QMessageBox.Yes:
				self.update_declined.emit()
				self.reject()
		else:
			# Normal decline
			self.update_declined.emit()
			self.reject()

	def update_download_progress(self, progress):
		"""Update the download progress bar."""
		self.progress_bar.setValue(progress)
		self.status_label.setText(f"Downloading... {progress}%")

	def download_complete(self, file_path):
		"""Handle download completion."""
		self.download_completed = True
		self.file_path = file_path
		
		# Update progress to 100% if not already
		self.progress_bar.setValue(100)
		self.status_label.setText("Download complete! Verifying...")

	def verification_started(self):
		"""Handle verification start."""
		self.status_label.setText("Verifying download integrity...")

	def verification_success(self, file_path, actual_checksum, expected_checksum):
		"""Handle successful verification."""
		# Update UI for installation mode
		self.yes_button.setEnabled(True)
		self.yes_button.setText("Install")
		self.yes_button.setStyleSheet("""
			QPushButton {
				background-color: #2196F3;
				color: white;
				border: none;
				border-radius: 5px;
				font-weight: bold;
			}
			QPushButton:hover {
				background-color: #1976D2;
			}
			QPushButton:pressed {
				background-color: #1565C0;
			}
		""")
		
		self.no_button.setText("Close")
		self.progress_bar.setVisible(False)
		self.status_label.setText("✓ Verification successful")
		self.status_label.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: bold;")
		
		# Update message with platform-specific installation instructions
		install_msg = ("Download Complete!\n\n"
					  "The update has been downloaded and verified.\n\n" +
					  self.platform_manager.update_manager.get_installation_instructions())
		self.message_label.setText(install_msg)

	def verification_failed(self, error_msg):
		"""Handle verification failure."""
		self.download_failed = True
		
		# Update UI for failure
		self.yes_button.setEnabled(True)
		self.yes_button.setText("Retry")
		self.no_button.setText("Close")
		
		self.progress_bar.setVisible(False)
		self.status_label.setText("✗ Verification failed")
		self.status_label.setStyleSheet("font-size: 12px; color: #F44336; font-weight: bold;")
		
		# Update message
		self.message_label.setText(
			f"Download verification failed!\n\n"
			f"Error: {error_msg}\n\n"
			"The downloaded file may be corrupted or tampered with.\n"
			"Please try downloading again."
		)

	def install_update(self):
		"""Open the downloaded update file."""
		if self.file_path and os.path.exists(self.file_path):
			# Open the update file using platform manager
			if self.platform_manager.update_manager.open_update_file(self.file_path):
				# Show a reminder to quit the app (for all platforms)
				msg = QMessageBox(self)
				msg.setWindowTitle("Quit Application")
				msg.setText("Please quit this application to complete the installation.")
				msg.setInformativeText("Follow the installer instructions to complete the update.")
				msg.setStandardButtons(QMessageBox.Ok)
				msg.setDefaultButton(QMessageBox.Ok)
				msg.exec_()
			else:
				# Failed to open the update file
				msg = QMessageBox(self)
				msg.setWindowTitle("Error")
				msg.setText("Failed to open the update file.")
				msg.setInformativeText(f"Please manually open: {self.file_path}")
				msg.setIcon(QMessageBox.Warning)
				msg.exec_()

			# Close the dialog
			self.accept()