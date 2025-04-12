import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
							 QPushButton, QDialog, QSizePolicy, QSpacerItem,
							 QProgressBar)


class UpdateView(QDialog):
	"""
	Widget for displaying current app version, new app version.
	Also contains a yes and no box to ask the user whether they want to install the update.
	"""

	# Signals to communicate user's choice
	update_accepted = pyqtSignal()
	update_declined = pyqtSignal()

	def __init__(self, current_version, new_version, parent=None):
		super().__init__(parent)
		self.current_version = current_version
		self.new_version = new_version

		self.setWindowTitle("Update Available")
		self.setFixedWidth(300)
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

		# Progress bar (initially hidden)
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.progress_bar.setVisible(False)  # Hide initially
		self.progress_label = QLabel("Downloading update...")
		self.progress_label.setAlignment(Qt.AlignCenter)
		self.progress_label.setVisible(False)  # Hide initially

		main_layout.addWidget(self.progress_label)
		main_layout.addWidget(self.progress_bar)

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
		# Hide the question and buttons
		self.question_label.setVisible(False)
		self.yes_button.setVisible(False)
		self.no_button.setVisible(False)

		# Show progress elements
		self.progress_label.setVisible(True)
		self.progress_bar.setVisible(True)

		# Update window title
		self.setWindowTitle("Downloading Update")

	def update_progress(self, progress):
		"""Update the progress bar value."""
		self.progress_bar.setValue(progress)

		# If download is complete, change the message
		if progress >= 100:
			self.progress_label.setText("Download complete! Installing...")

	def download_complete(self, file_path):
		"""Called when download is complete."""
		from PyQt5.QtWidgets import QScrollArea, QFrame

		self.file_path = file_path  # Store the file path for later use

		# Update UI
		self.progress_label.setText("Download Complete")
		self.progress_bar.setValue(100)

		# Clear existing buttons
		for i in reversed(range(self.buttons_layout.count())):
			item = self.buttons_layout.itemAt(i)
			if item and item.widget():
				item.widget().deleteLater()

		# Create installation instructions label
		instruction_text = (
			"To install the update:\n\n"
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

		# Add "Open Installer" button
		open_button = QPushButton("Open Installer")
		open_button.clicked.connect(self._open_installer)
		self.buttons_layout.addWidget(open_button)

		# Add "Update Later" button
		later_button = QPushButton("Update Later")
		later_button.clicked.connect(self.accept)
		self.buttons_layout.addWidget(later_button)

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
