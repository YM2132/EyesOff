import webbrowser
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
							 QPushButton, QLineEdit, QMessageBox, QFrame)
from PyQt5.QtGui import QFont, QKeyEvent
from utils.constants import PURCHASE_URL
from utils.licensing.manager import LicensingManager


class TrialExpiredDialog(QDialog):
	"""Modal dialog shown when trial has expired."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.licensing_manager = LicensingManager()
		self.setWindowTitle("Trial Expired - EyesOff")
		self.setModal(True)
		self.setFixedSize(450, 350)

		# Make dialog uncloseable
		self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
		self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

		self._init_ui()

	def _init_ui(self):
		"""Initialize the UI components."""
		layout = QVBoxLayout()
		layout.setSpacing(20)
		layout.setContentsMargins(30, 30, 30, 30)

		# Title
		title_label = QLabel("Your EyesOff Trial Has Expired")
		title_font = QFont()
		title_font.setPointSize(18)
		title_font.setBold(True)
		title_label.setFont(title_font)
		title_label.setAlignment(Qt.AlignCenter)
		layout.addWidget(title_label)

		# Message
		message_label = QLabel(
			"Thank you for trying EyesOff! Your 14-day trial has ended.\n"
			"Please purchase the Pro version to continue using the app."
		)
		message_label.setWordWrap(True)
		message_label.setAlignment(Qt.AlignCenter)
		layout.addWidget(message_label)

		# Purchase button
		purchase_button = QPushButton("Purchase EyesOff Pro")
		purchase_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
        """)
		purchase_button.clicked.connect(self._open_purchase_url)
		layout.addWidget(purchase_button)

		# Separator
		separator = QFrame()
		separator.setFrameShape(QFrame.HLine)
		separator.setStyleSheet("background-color: #E0E0E0;")
		layout.addWidget(separator)

		# Error message label (hidden by default)
		self.error_label = QLabel()
		self.error_label.setStyleSheet("color: red; font-size: 12px;")
		self.error_label.setAlignment(Qt.AlignCenter)
		self.error_label.setVisible(False)
		layout.addWidget(self.error_label)

		# Bottom buttons
		button_layout = QHBoxLayout()
		button_layout.setSpacing(10)

		self.exit_button = QPushButton("Exit")
		self.exit_button.clicked.connect(self._exit_app)

		button_layout.addWidget(self.exit_button)
		layout.addLayout(button_layout)

		self.setLayout(layout)

	def _open_purchase_url(self):
		"""Open the purchase URL in the default browser."""
		webbrowser.open(PURCHASE_URL)

	def _exit_app(self):
		"""Exit the application."""
		self.reject()  # Close dialog with failure

	def keyPressEvent(self, event: QKeyEvent):
		"""Override key press to prevent ESC from closing dialog."""
		if event.key() == Qt.Key_Escape:
			# Ignore ESC key
			event.ignore()
		else:
			super().keyPressEvent(event)

	def closeEvent(self, event):
		"""Override close event to prevent closing."""
		event.ignore()