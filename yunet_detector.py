import cv2 as cv
import numpy as np
import math
from typing import Tuple, List, Optional

from utils.yunet import YuNet


class YuNetDetector:
	"""
	Face detection implementation using YuNet face detection models.
	"""

	def __init__(self, model_path: str, confidence_threshold: float = 0.75, nms_threshold: float = 0.3,
				 top_k: int = 2500):
		"""
		Initialize the YuNet face detector.

		Args:
			model_path (str): Path to the YuNet face detection model
			confidence_threshold (float): Minimum confidence threshold for detection (0.0-1.0)
			nms_threshold (float): Used to eliminate redundant and overlapping bounding boxes
			top_k (int): Limits the maximum number of detection candidates to consider before applying NMS
		"""
		self.confidence_threshold = confidence_threshold
		self.target_size = 340

		backend_id = cv.dnn.DNN_BACKEND_OPENCV
		target_id = cv.dnn.DNN_TARGET_CPU

		# Initialize the detector
		self.detector = YuNet(
			modelPath=model_path,
			inputSize=[self.target_size, self.target_size],
			confThreshold=confidence_threshold,
			nmsThreshold=nms_threshold,
			topK=top_k,
			backendId=backend_id,
			targetId=target_id
		)

	def detect(self, frame: np.ndarray) -> Tuple[int, List[Tuple[int, int, int, int]], np.ndarray]:
		"""
		Detect faces in the given frame.

		Args:
			frame (np.ndarray): Input image frame

		Returns:
			Tuple containing:
				- Number of faces detected
				- List of bounding boxes [x, y, width, height]
				- Annotated frame with visualizations
		"""
		# Resize frame while maintaining aspect ratio
		h, w = frame.shape[:2]
		scale_factor = self.target_size / max(h, w)
		new_w = int(w * scale_factor)
		new_h = int(h * scale_factor)
		resized = cv.resize(frame, (new_w, new_h))

		# Run face detection
		self.detector.setInputSize([new_w, new_h])
		detections = self.detector.infer(resized)

		# Extract bounding boxes and scale back to original size
		bboxes = []
		if detections.shape[0] > 0:
			# Scale factor to convert back to original size
			inverse_scale = 1.0 / scale_factor

			# For visualization, create a compatible detection result format
			detection_result = self._prepare_visualization_data(detections, frame, inverse_scale)

			# Extract bounding boxes in the expected format
			for det in detections:
				if det[-1] >= self.confidence_threshold:  # Check confidence
					# Scale back to original coordinates
					x = int(det[0] * inverse_scale)
					y = int(det[1] * inverse_scale)
					w = int(det[2] * inverse_scale)
					h = int(det[3] * inverse_scale)
					bboxes.append((x, y, w, h))
		else:
			# Create empty detection result
			detection_result = type('', (), {'detections': []})()

		# Create visualized frame
		annotated_frame = self._visualize(frame, detection_result)

		return len(bboxes), bboxes, annotated_frame

	def _prepare_visualization_data(self, detections, frame, inverse_scale):
		"""
		Prepare detection data in a format compatible with the visualization method.

		Args:
			detections: Raw detection results from YuNet
			frame: Original input frame
			inverse_scale: Scale factor to convert from resized to original coordinates

		Returns:
			Object with detections in the format expected by _visualize
		"""
		# Create structure to hold detections
		DetectionResult = type('DetectionResult', (), {'detections': []})

		for det in detections:
			if det[-1] >= self.confidence_threshold:
				# Scale coordinates back to original image
				x = int(det[0] * inverse_scale)
				y = int(det[1] * inverse_scale)
				w = int(det[2] * inverse_scale)
				h = int(det[3] * inverse_scale)

				# Create bounding box object
				bbox = type('BoundingBox', (), {
					'origin_x': x,
					'origin_y': y,
					'width': w,
					'height': h
				})()

				# Create category with score
				category = type('Category', (), {'score': det[-1]})()

				# Create keypoints (5 facial landmarks)
				keypoints = []
				img_h, img_w = frame.shape[:2]
				for j in range(4, 14, 2):
					kp_x = det[j] * inverse_scale / img_w  # Normalize to 0-1
					kp_y = det[j + 1] * inverse_scale / img_h
					keypoints.append(type('Keypoint', (), {'x': kp_x, 'y': kp_y})())

				# Create detection with all components
				detection = type('Detection', (), {
					'bounding_box': bbox,
					'categories': [category],
					'keypoints': keypoints
				})()

				DetectionResult.detections.append(detection)

		return DetectionResult

	def _normalized_to_pixel_coordinates(
			self, normalized_x: float, normalized_y: float,
			image_width: int, image_height: int) -> Optional[Tuple[int, int]]:
		"""
		Converts normalized coordinates to pixel coordinates.

		Args:
			normalized_x: Normalized x coordinate
			normalized_y: Normalized y coordinate
			image_width: Width of the image
			image_height: Height of the image

		Returns:
			Tuple of pixel coordinates or None if invalid
		"""

		# Check if coordinates are valid (between 0 and 1)
		def is_valid_normalized_value(value: float) -> bool:
			return (value > 0 or math.isclose(0, value)) and (value < 1 or math.isclose(1, value))

		if not (is_valid_normalized_value(normalized_x) and is_valid_normalized_value(normalized_y)):
			return None

		x_px = min(math.floor(normalized_x * image_width), image_width - 1)
		y_px = min(math.floor(normalized_y * image_height), image_height - 1)
		return x_px, y_px

	def _visualize(self, image: np.ndarray, detection_result) -> np.ndarray:
		"""
		Draw bounding boxes and keypoints on the input image.

		Args:
			image: The input RGB image
			detection_result: The face detection results

		Returns:
			Image with bounding boxes and keypoints
		"""
		# Constants for visualization
		MARGIN = 10  # pixels
		ROW_SIZE = 10  # pixels
		FONT_SIZE = 1
		FONT_THICKNESS = 1
		TEXT_COLOR = (255, 0, 0)  # red (BGR)

		annotated_image = image.copy()
		height, width, _ = image.shape

		for detection in detection_result.detections:
			# Draw bounding_box
			bbox = detection.bounding_box
			start_point = bbox.origin_x, bbox.origin_y
			end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
			cv.rectangle(annotated_image, start_point, end_point, TEXT_COLOR, 3)

			# Draw keypoints
			for keypoint in detection.keypoints:
				keypoint_px = self._normalized_to_pixel_coordinates(keypoint.x, keypoint.y, width, height)
				if keypoint_px:
					color, thickness, radius = (0, 255, 0), 2, 2
					cv.circle(annotated_image, keypoint_px, radius, color, thickness)

			# Draw label and confidence score
			category = detection.categories[0]
			probability = round(category.score, 2)
			result_text = f"Face: {probability:.2f}"
			text_location = (MARGIN + bbox.origin_x, MARGIN + ROW_SIZE + bbox.origin_y)
			cv.putText(annotated_image, result_text, text_location,
					   cv.FONT_HERSHEY_PLAIN, FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)

		return annotated_image