import os
import time
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
							 QPushButton, QDialog, QSizePolicy, QSpacerItem,
							 QProgressBar, QMessageBox, QScrollArea, QFrame)

class UpdateView(QDialog):
	"""
	Widget for displaying current app version, new app version.
	Also contains a yes and no box to ask the user whether they want to install the update.
	"""

	# Signals to communicate user's choice
	update_accepted = pyqtSignal()
	update_declined = pyqtSignal()
	
	# States for update process
	STATE_INITIAL = 0
	STATE_DOWNLOADING = 1
	STATE_VERIFYING = 2
	STATE_VERIFIED = 3
	STATE_VERIFICATION_FAILED = 4

	def __init__(self, current_version, new_version, parent=None):
		super().__init__(parent)
		self.current_version = current_version
		self.new_version = new_version
		self.state = self.STATE_INITIAL
		self.file_path = None
		self.verification_error = None

		self.setWindowTitle("Update Available")
		self.setFixedWidth(400)  # Increased width for verification UI
		self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)

		self.init_ui()

	def init_ui(self):
		# Main layout
		main_layout = QVBoxLayout()
		main_layout.setSpacing(10)

		# Title label
		title_label = QLabel("Update Available")
		title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
		title_label.setAlignment(Qt.AlignCenter)
		main_layout.addWidget(title_label)

		# Version information
		version_layout = QVBoxLayout()

		current_version_label = QLabel(f"Current version: {self.current_version}")
		new_version_label = QLabel(f"New version: {self.new_version}")

		version_layout.addWidget(current_version_label)
		version_layout.addWidget(new_version_label)
		main_layout.addLayout(version_layout)

		# Question label
		self.question_label = QLabel("Would you like to update now?")
		self.question_label.setAlignment(Qt.AlignCenter)
		main_layout.addWidget(self.question_label)

		# Progress section (initially hidden)
		self.progress_section = QWidget()
		progress_layout = QVBoxLayout(self.progress_section)
		progress_layout.setContentsMargins(0, 0, 0, 0)
		
		# Progress label and bar
		self.progress_label = QLabel("Downloading update...")
		self.progress_label.setAlignment(Qt.AlignCenter)
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		
		progress_layout.addWidget(self.progress_label)
		progress_layout.addWidget(self.progress_bar)
		
		# Verification status section
		self.verification_widget = QWidget()
		verification_layout = QVBoxLayout(self.verification_widget)
		verification_layout.setContentsMargins(0, 5, 0, 5)
		
		self.verification_label = QLabel("Verifying download...")
		self.verification_label.setAlignment(Qt.AlignCenter)
		self.verification_label.setStyleSheet("font-weight: bold;")
		verification_layout.addWidget(self.verification_label)
		
		# Status details
		self.verification_details = QLabel("Checking file integrity...")
		self.verification_details.setAlignment(Qt.AlignCenter)
		self.verification_details.setWordWrap(True)
		verification_layout.addWidget(self.verification_details)
		
		progress_layout.addWidget(self.verification_widget)
		self.verification_widget.setVisible(False)
		
		# Add progress section to main layout
		main_layout.addWidget(self.progress_section)
		self.progress_section.setVisible(False)

		# Buttons layout
		self.buttons_layout = QHBoxLayout()

		# Add a spacer to push buttons to the center
		self.buttons_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

		# Yes button
		self.yes_button = QPushButton("Yes")
		self.yes_button.clicked.connect(self._on_yes_clicked)
		self.buttons_layout.addWidget(self.yes_button)

		# No button
		self.no_button = QPushButton("No")
		self.no_button.clicked.connect(self._on_no_clicked)
		self.buttons_layout.addWidget(self.no_button)

		# Add another spacer
		self.buttons_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

		main_layout.addLayout(self.buttons_layout)

		self.setLayout(main_layout)

	def _on_yes_clicked(self):
		self._show_download_progress()

		from PyQt5.QtCore import QTimer
		QTimer.singleShot(100, self.update_accepted.emit)

	def _on_no_clicked(self):
		self.update_declined.emit()
		self.reject()  # Close the dialog

	def _show_download_progress(self):
		"""Switch the UI to download progress mode."""
		self.state = self.STATE_DOWNLOADING
		
		# Hide the question and buttons
		self.question_label.setVisible(False)
		self.yes_button.setVisible(False)
		self.no_button.setVisible(False)

		# Show progress section
		self.progress_section.setVisible(True)
		self.verification_widget.setVisible(False)
		self.progress_label.setText("Downloading update...")
		
		# Update window title
		self.setWindowTitle("Downloading Update")

	def update_progress(self, progress):
		"""Update the progress bar value."""
		self.progress_bar.setValue(progress)

		# If download is complete, change the message
		if progress >= 100:
			self.progress_label.setText("Download complete!")
			
	def show_verification_started(self):
		"""Show that verification has started."""
		self.state = self.STATE_VERIFYING
		self.setWindowTitle("Verifying Update")
		self.verification_widget.setVisible(True)
		self.verification_label.setText("Verifying download...")
		self.verification_details.setText("Checking file integrity and authenticity...")

	def show_verification_success(self, file_path, local_checksum, remote_checksum):
		"""Show that verification was successful."""
		self.state = self.STATE_VERIFIED
		self.file_path = file_path

		# Create container for verification info with simplified layout
		container = QWidget()
		layout = QVBoxLayout(container)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(3)

		# Update verification status and details
		self.verification_label.setText("Verification Successful")
		self.verification_label.setStyleSheet("font-weight: bold; color: green;")
		self.verification_details.setText(f"The downloaded update has been verified as authentic and safe to install.")
		self.verification_details.setWordWrap(True)  # Enable soft text wrapping

		# Add the labels to the container
		layout.addWidget(self.verification_label)
		layout.addWidget(self.verification_details)

		# Create scroll area and configure it
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.NoFrame)
		scroll.setWidget(container)
		scroll.setMinimumHeight(80)

		# Add to main layout
		self.layout().insertWidget(4, scroll)
		
	def show_verification_failed(self, error_message):
		"""Show that verification failed."""
		self.state = self.STATE_VERIFICATION_FAILED
		self.verification_error = error_message
		
		self.verification_label.setText("Verification Failed")
		self.verification_label.setStyleSheet("font-weight: bold; color: red;")
		self.verification_details.setText(
			f"The downloaded update could not be verified as authentic. "
			f"This could indicate tampering or corruption.\n\nError: {error_message}"
		)
		
		# Change progress bar to red to indicate failure
		self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
		
		# Show a close button
		self._reset_buttons()
		close_button = QPushButton("Close")
		close_button.clicked.connect(self.reject)
		self.buttons_layout.addWidget(close_button)

	def _reset_buttons(self):
		"""Clear all buttons from the button layout."""
		for i in reversed(range(self.buttons_layout.count())):
			item = self.buttons_layout.itemAt(i)
			if item:
				if item.widget():
					item.widget().deleteLater()
				elif item.spacerItem():
					self.buttons_layout.removeItem(item)
					
	def download_complete(self, file_path):
		"""Called when download is complete and verification succeeded."""
		
		if self.state == self.STATE_VERIFICATION_FAILED:
			# Don't proceed if verification failed
			return
		
		self.file_path = file_path  # Store the file path for later use
		
		# Set progress to 100% just in case
		# self.progress_bar.setValue(100)
		
		# Clear existing buttons
		self._reset_buttons()
		
		# Create installation instructions label
		instruction_text = (
			"To install the verified update:\n\n"
			"1. Click 'Open Installer'\n"
			"2. Quit this application when prompted\n"
			"3. Drag the new version to Applications folder\n"
			"4. Restart the application"
		)
		
		# Create scrollable area for instructions
		self.instruction_label = QLabel(instruction_text)
		self.instruction_label.setWordWrap(True)
		self.instruction_label.setStyleSheet("margin: 10px;")
		
		# Create a scroll area
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		scroll_area.setFrameShape(QFrame.NoFrame)  # Remove the frame border
		scroll_area.setWidget(self.instruction_label)
		scroll_area.setMinimumHeight(100)  # Set minimum height
		
		# Add the scroll area to the layout
		self.layout().insertWidget(3, scroll_area)
		
		# Add buttons with spacers for centering
		self.buttons_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
		
		# Add "Open Installer" button
		open_button = QPushButton("Open Installer")
		open_button.clicked.connect(self._open_installer)
		self.buttons_layout.addWidget(open_button)
		
		# Add "Update Later" button
		later_button = QPushButton("Update Later")
		later_button.clicked.connect(self.accept)
		self.buttons_layout.addWidget(later_button)
		
		self.buttons_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

	def _open_installer(self):
		"""Open the installer and show quit reminder."""
		import subprocess
		import sys
		from PyQt5.QtWidgets import QMessageBox

		# Open the DMG file
		if sys.platform == "darwin":
			subprocess.Popen(['open', self.file_path])

			# Show a reminder to quit the app
			msg = QMessageBox(self)
			msg.setWindowTitle("Quit Application")
			msg.setText("Please quit this application to complete the installation.")
			msg.setInformativeText("After quitting, drag EyesOff to the application folder :)")
			msg.setStandardButtons(QMessageBox.Ok)
			msg.setDefaultButton(QMessageBox.Ok)
			msg.exec_()

		else:
			# For non-macOS platforms, just try to open the file
			if sys.platform == "win32":
				os.startfile(self.file_path)
			else:
				subprocess.Popen(['xdg-open', self.file_path])

		# Close the dialog
		self.accept()
