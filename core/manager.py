import logging
import time
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QWaitCondition

# Import the detection manager
from DetectionManager import DetectionManager


class DetectionManagerSignals(QObject):
	"""Signals for the detection manager thread."""
	# Signal emitted when an alert state changes
	alert_state_changed = pyqtSignal(bool)
	# Signal emitted when detection statistics are updated
	stats_updated = pyqtSignal(dict)
	# Signal emitted when an error occurs
	error_occurred = pyqtSignal(str)
	# Signal emitted when the manager is stopped
	manager_stopped = pyqtSignal()
	# Signal emitted when an alert should be shown
	show_alert = pyqtSignal()
	# Signal emitted when an alert should be dismissed
	dismiss_alert = pyqtSignal()


class DetectionManagerThread(QThread):
	"""
	Thread for running the detection manager.
	This separates the detection and alert processing from the UI thread.
	"""
	
	def __init__(self, settings: Dict[str, Any]):
		"""
		Initialize the detection manager thread.
		
		Args:
			settings: Settings for the detection manager
		"""
		super().__init__()
		self.settings = settings
		self.signals = DetectionManagerSignals()
		self.mutex = QMutex()
		self.condition = QWaitCondition()
		self.is_running = False
		self.is_paused = False
		self.current_face_count = 0
		self.detection_manager = None
		self.logger = self._setup_logger()

		# Variable to keep track of number of faces at last alert
		self.previous_face_count = 0
		self.num_faces_last_alert = 0
		
		# Add detection verification
		self.consecutive_detections = 0
		# TODO Simplify the detection delay we also have in the settings a debounce
		self.detection_delay_frames = 6  # About 0.2s at 30fps
		self.last_detection_state = False
		
		# Statistics
		self.stats = {
			"total_detections": 0,
			"alert_count": 0,
			"last_detection_time": None,
			"session_start_time": None,
			"face_counts": {}  # History of face counts
		}
	
	def _setup_logger(self):
		"""Set up logging for the detection manager thread."""
		logger = logging.getLogger("EyesOff_Manager_Thread")
		if not logger.handlers:
			logger.setLevel(logging.INFO)
			handler = logging.StreamHandler()
			formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
			handler.setFormatter(formatter)
			logger.addHandler(handler)
		return logger
	
	def run(self):
		"""Run the detection manager thread."""
		try:
			self.mutex.lock()
			self.is_running = True
			self.is_paused = False
			self.mutex.unlock()
			
			# Initialize the detection manager
			self._init_detection_manager()
			
			# Record session start time
			self.stats["session_start_time"] = time.time()
			
			self.logger.info("Detection manager thread started")
			
			while self.is_running:
				self.mutex.lock()
				if self.is_paused:
					self.condition.wait(self.mutex)
				self.mutex.unlock()
				
				if not self.is_running:
					break
				
				# Process the current face count
				self._process_detection(self.current_face_count)
				
				# Short sleep to prevent high CPU usage
				time.sleep(0.05)
			
			self.logger.info("Detection manager thread stopped")
			self._cleanup()
			
		except Exception as e:
			self.logger.error(f"Error in detection manager thread: {e}")
			self.signals.error_occurred.emit(f"Detection manager error: {e}")
			self._cleanup()
	
	def _init_detection_manager(self):
		"""Initialize the detection manager with the current settings."""
		try:
			# Create the detection manager with settings
			self.detection_manager = DetectionManager(
				face_threshold=self.settings.get('face_threshold', 1),
				debounce_time=self.settings.get('debounce_time', 1.0),
				alert_duration=self.settings.get('alert_duration', None),
				alert_color=self.settings.get('alert_color', (0, 0, 255)),
				alert_opacity=self.settings.get('alert_opacity', 0.8),
				alert_size=self.settings.get('alert_size', (600, 300)),
				alert_position=self.settings.get('alert_position', 'center'),
				enable_animations=self.settings.get('enable_animations', True)
			)
		except Exception as e:
			self.logger.error(f"Error initializing detection manager: {e}")
			self.signals.error_occurred.emit(f"Error initializing detection manager: {e}")

	def _process_detection(self, face_count: int):
		"""Process the detection result."""
		if not self.detection_manager:
			return

		try:
			# Update statistics
			self.stats["total_detections"] += 1
			self.stats["last_detection_time"] = time.time()

			# Track face count history
			face_key = str(face_count)
			if face_key in self.stats["face_counts"]:
				self.stats["face_counts"][face_key] += 1
			else:
				self.stats["face_counts"][face_key] = 1

			# Check if we need to show an alert based on face count and threshold
			threshold = self.settings.get('face_threshold', 1)
			multiple_viewers_detected = face_count > threshold

			# Get current alert state
			was_alert_showing = self.detection_manager.is_alert_showing

			# Track the previous face count
			if not hasattr(self, 'previous_face_count'):
				self.previous_face_count = face_count

			# Detect if face count increased
			face_count_increased = face_count > self.previous_face_count

			# Update detection state with verification delay
			if multiple_viewers_detected != self.last_detection_state:
				# Detection state changed, reset counter
				self.consecutive_detections = 1
				self.last_detection_state = multiple_viewers_detected
			else:
				# Same detection state, increment counter
				self.consecutive_detections += 1

			# Reset tracking when we go below threshold
			if not multiple_viewers_detected:
				self.num_faces_last_alert = 0

			# Only trigger alerts after seeing consistent detections for the delay period
			if self.consecutive_detections >= self.detection_delay_frames:
				# Show alert if:
				# 1. Multiple viewers are detected
				# 2. No alert is currently showing
				# 3. Either:
				#    a. Face count increased from previous reading, OR
				#    b. We're coming from below threshold (num_faces_last_alert is 0)
				print(
					f"DEBUG: multiple_viewers={multiple_viewers_detected}, was_alert_showing={was_alert_showing}, face_count={face_count}, threshold={threshold}, consecutive={self.consecutive_detections}")

				if multiple_viewers_detected and not was_alert_showing and (
						face_count_increased or self.num_faces_last_alert == 0):
					self.logger.info(f"Multiple viewers detected ({face_count})! Showing privacy alert.")
					self.detection_manager.is_alert_showing = True
					# Update tracking for last alerted face count
					self.num_faces_last_alert = face_count
					# Reset consecutive detection counter
					self.consecutive_detections = 0
					self.signals.show_alert.emit()
					self.stats["alert_count"] += 1
					self.signals.alert_state_changed.emit(True)

				elif not multiple_viewers_detected and was_alert_showing:
					print("BELOW THRESHOLD")
					self.logger.info("No unauthorized viewers detected. Hiding alert.")
					self.detection_manager.is_alert_showing = False
					# Reset tracking
					self.num_faces_last_alert = 0
					# Send signal to GUI to dismiss alert
					self.signals.dismiss_alert.emit()
					self.signals.alert_state_changed.emit(False)

			# Update previous face count for next iteration
			self.previous_face_count = face_count

			# Emit updated statistics periodically
			if self.stats["total_detections"] % 10 == 0:
				self.signals.stats_updated.emit(self.stats.copy())

		except Exception as e:
			self.logger.error(f"Error processing detection: {e}")
			self.signals.error_occurred.emit(f"Error processing detection: {e}")

	def handle_user_dismissal(self):
		"""Handle when a user manually dismisses an alert."""
		if self.detection_manager:
			self.detection_manager.is_alert_showing = False

		# emit signal to remove the exclamation mark
		self.signals.alert_state_changed.emit(False)

		self.num_faces_last_alert = self.current_face_count
		self.logger.info(f"Alert manually dismissed by user. Last alert face count: {self.num_faces_last_alert}")
		print(f"num_faces_last_alert after user dismiss: {self.current_face_count}")
	
	def update_face_count(self, face_count: int):
		"""
		Update the current face count.
		
		Args:
			face_count: Number of faces detected
		"""
		self.mutex.lock()
		self.current_face_count = face_count
		self.mutex.unlock()
	
	def update_settings(self, settings: Dict[str, Any]):
		"""
		Update detection manager settings.
		
		Args:
			settings: New settings for the detection manager
		"""
		self.mutex.lock()
		self.settings.update(settings)
		
		# Update detection delay frames based on settings
		if 'detection_delay' in settings:
			# Convert time in seconds to frames (assuming 30fps)
			delay_seconds = settings['detection_delay']
			self.detection_delay_frames = max(1, int(delay_seconds * 30))
		
		# Update the detection manager if it exists
		if self.detection_manager:
			self.detection_manager.update_settings(settings)
			
		self.mutex.unlock()
	
	def pause(self):
		"""Pause the detection manager thread."""
		self.mutex.lock()
		self.is_paused = True
		self.mutex.unlock()
	
	def resume(self):
		"""Resume the detection manager thread."""
		self.mutex.lock()
		self.is_paused = False
		self.condition.wakeAll()
		self.mutex.unlock()
	
	def stop(self):
		"""Stop the detection manager thread."""
		self.mutex.lock()
		self.is_running = False
		self.condition.wakeAll()
		self.mutex.unlock()

	def _cleanup(self):
		"""Clean up resources when the thread stops."""
		# Cleanup the detection manager
		self.detection_manager.is_alert_showing = False
		self.detection_manager = None

		# Upon stopping monitoring we reset the number of detections.
		self.consecutive_detections = 0

		# Send signal to GUI to dismiss alert
		self.signals.dismiss_alert.emit()
		self.signals.manager_stopped.emit()
