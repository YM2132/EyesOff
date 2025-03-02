import cv2
import numpy as np
import logging
from threading import Thread, Lock
import time


class DetectionManager:
	"""
	Simple detection manager that shows a privacy alert when unauthorized viewers are detected.
	Uses OpenCV to display visual warnings directly on the screen.
	"""

	def __init__(self):
		"""Initialize the detection manager."""
		self.is_alert_showing = False
		self.logger = self._setup_logger()
		self.alert_window_name = "PRIVACY ALERT - EYES OFF!!!"
		self.lock = Lock()

	def _setup_logger(self):
		"""Set up logging for the detection manager."""
		logger = logging.getLogger("EyesOff")
		logger.setLevel(logging.INFO)
		handler = logging.StreamHandler()
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		return logger

	def process_detection(self, multiple_viewers_detected):
		"""
		Process the detection result and show/hide warning accordingly.

		Args:
			multiple_viewers_detected (bool): True if multiple viewers are detected
		"""
		with self.lock:
			if multiple_viewers_detected and not self.is_alert_showing:
				# Show alert if multiple viewers detected and no alert is currently showing
				self.logger.info("Multiple viewers detected! Showing privacy alert.")
				Thread(target=self._show_privacy_alert, daemon=True).start()
			elif not multiple_viewers_detected and self.is_alert_showing:
				# Hide alert if no multiple viewers and alert is showing
				self.logger.info("No unauthorized viewers detected. Hiding alert.")
				self._dismiss_alert()

	def _show_privacy_alert(self):
		"""Display a privacy alert using OpenCV."""
		try:
			with self.lock:
				self.is_alert_showing = True

			# Create a warning display (red background with text)
			height, width = 300, 600
			alert_img = np.zeros((height, width, 3), dtype=np.uint8)
			alert_img[:] = (0, 0, 255)  # Red background (BGR format)

			# Add warning text
			font = cv2.FONT_HERSHEY_DUPLEX
			cv2.putText(alert_img, "EYES OFF!!!", (120, 100), font, 2, (255, 255, 255), 4)
			cv2.putText(alert_img, "Privacy Alert", (180, 150), font, 1, (255, 255, 255), 2)
			cv2.putText(alert_img, "Someone else is looking at your screen!", (50, 200), font, 0.8, (255, 255, 255), 1)
			cv2.putText(alert_img, "Press any key to dismiss", (170, 250), font, 0.7, (255, 255, 255), 1)

			# Create window and show the alert
			cv2.namedWindow(self.alert_window_name, cv2.WINDOW_NORMAL)
			cv2.setWindowProperty(self.alert_window_name, cv2.WND_PROP_TOPMOST, 1)  # Make it stay on top
			cv2.imshow(self.alert_window_name, alert_img)

			# Wait for key press to dismiss
			cv2.waitKey(0)
			self._dismiss_alert()

		except Exception as e:
			self.logger.error(f"Error showing alert: {e}")
			with self.lock:
				self.is_alert_showing = False

	def _dismiss_alert(self):
		"""Dismiss the privacy alert."""
		with self.lock:
			if self.is_alert_showing:
				cv2.destroyWindow(self.alert_window_name)
				self.is_alert_showing = False

	def stop(self):
		"""Stop the detection manager and clean up."""
		self._dismiss_alert()
		cv2.destroyAllWindows()


# Example of how to integrate with a webcam feed:
def webcam_detection_example():
	"""Example of integrating DetectionManager with webcam feed."""
	# Create the detection manager
	detection_mgr = DetectionManager()

	# Open webcam
	cap = cv2.VideoCapture(0)
	if not cap.isOpened():
		print("Error: Could not open webcam")
		return

	# Create a named window for the webcam feed
	window_name = "EyesOff - Webcam Feed"
	cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

	last_detection_time = time.time()
	detection_interval = 1.0  # Check for multiple viewers every second

	try:
		print("Starting EyesOff with webcam...")
		print("Press 'q' to exit")

		while True:
			# Read frame from webcam
			ret, frame = cap.read()
			if not ret:
				print("Error: Failed to capture frame")
				break

			# Display the current frame
			cv2.imshow(window_name, frame)

			# Check for multiple viewers periodically
			current_time = time.time()
			if current_time - last_detection_time > detection_interval:
				last_detection_time = current_time

				# Here you would normally pass the frame to your AI model
				# For the example, we'll simulate random detections
				import random
				multiple_viewers_detected = random.choice([True, False])

				print(
					f"Detection state: {'Multiple viewers detected' if multiple_viewers_detected else 'Only authorized user'}")
				detection_mgr.process_detection(multiple_viewers_detected)

			# Check for exit key
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break

	except KeyboardInterrupt:
		print("\nShutting down EyesOff...")
	finally:
		# Clean up
		detection_mgr.stop()
		cap.release()
		cv2.destroyAllWindows()


# Example of simulated detection without webcam:
if __name__ == "__main__":
	# Choose which example to run
	use_webcam = False

	if use_webcam:
		webcam_detection_example()
	else:
		# Create the detection manager
		detection_mgr = DetectionManager()

		# Simulate detections
		import random

		try:
			print("Starting EyesOff detection simulation...")
			print("Press Ctrl+C to exit")

			while True:
				# Simulate random detection events
				unauthorized_detected = random.choice([True, False])
				print(
					f"Detection state: {'Multiple viewers detected' if unauthorized_detected else 'Only authorized user'}")
				detection_mgr.process_detection(unauthorized_detected)

				# Sleep to simulate frame processing time
				time.sleep(2)

		except KeyboardInterrupt:
			print("\nShutting down EyesOff...")
			detection_mgr.stop()