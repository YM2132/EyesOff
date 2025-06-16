import math
import os
import random
from typing import Tuple, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from colour import Color

from utils.yunet import YuNet
from utils.resource_path import resource_path

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def preprocess(image_bgr: np.ndarray, size: int = 224) -> np.ndarray:
    """
    Mimics torchvision.Compose([
        Resize(224), CenterCrop(224), ToTensor(), Normalize(...)
    ])

    Args
    ----
    image_bgr : np.ndarray of shape (H, W, 3) in BGR uint8   (OpenCV default)
    size      : final square size (default 224)

    Returns
    -------
    np.ndarray of shape (3, size, size) – float32, normalised
    """
    # 1) Resize so the *shortest* side == `size`, keep aspect ratio
    h, w = image_bgr.shape[:2]
    if h < w:
        new_h, new_w = size, int(w * size / h)
    else:
        new_w, new_h = size, int(h * size / w)
    img = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 2) Centre-crop to `size` × `size`
    top  = (new_h - size) // 2
    left = (new_w - size) // 2
    img = img[top : top + size, left : left + size]

    # 3) BGR ➜ RGB, uint8 ➜ float32 0-1
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    # 4) C,H,W ordering
    img = np.transpose(img, (2, 0, 1))   # shape (3, size, size)

    # 5) Normalise with ImageNet statistics
    img = (img - _MEAN[:, None, None]) / _STD[:, None, None]

    return img

class GazeDetector:
	"""
	Eye contact detection using YuNet for face detection and a gaze estimation model.
	"""

	def __init__(self,
				 yunet_model_path: str,
				 gaze_model_path: str,
				 confidence_threshold: float = 0.75,
				 gaze_threshold: float = 0.6,
				 nms_threshold: float = 0.3,
				 top_k: int = 2500,
				 face_frame_skip: int = 2,  # Run face detection more frequently
				 gaze_frame_skip: int = 30,  # Run gaze analysis less frequently
				 use_onnx: bool = True):
		"""
		Initialize the gaze detector.

		Args:
			yunet_model_path: Path to the YuNet face detection model
			gaze_model_path: Path to the gaze estimation model (ONNX or PyTorch)
			confidence_threshold: Minimum confidence threshold for face detection
			gaze_threshold: Threshold for deciding if a person is looking at the screen
			nms_threshold: Used to eliminate redundant face bounding boxes
			top_k: Maximum number of face detection candidates
			frame_skip: Process every N frames to improve performance
			use_onnx: Whether to use the ONNX version of the gaze model
		"""
		self.confidence_threshold = confidence_threshold
		self.gaze_threshold = gaze_threshold
		self.target_size = 340
		self.use_onnx = use_onnx
		self.frame_count = 0

		# Separate counters for face and gaze processing
		self.face_frame_skip = face_frame_skip
		self.gaze_frame_skip = gaze_frame_skip
		self.frame_count = 0

		# Simple caches for faces and scores
		self.current_bboxes = []  # Current face bounding boxes
		self.current_scores = []  # Current gaze scores
		self.looking_bboxes = []  # Current looking faces

		self.last_bboxes = []
		self.last_scores = []
		self.last_looking_bboxes = []

		# Initialize face detector (YuNet)
		backend_id = cv2.dnn.DNN_BACKEND_OPENCV
		target_id = cv2.dnn.DNN_TARGET_CPU
		self.detector = YuNet(
			modelPath=yunet_model_path,
			inputSize=[self.target_size, self.target_size],
			confThreshold=confidence_threshold,
			nmsThreshold=nms_threshold,
			topK=top_k,
			backendId=backend_id,
			targetId=target_id,
		)

		# Initialize gaze model
		self.gaze_model_path = gaze_model_path
		self._init_gaze_model()

		# Set up transformations for the gaze model
		#self.transform = transforms.Compose([
	#		transforms.Resize(224),
	#		transforms.CenterCrop(224),
	#		transforms.ToTensor(),
	#		transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
	#	])

		# Visualization settings
		self.red = Color("red")
		self.colors = list(self.red.range_to(Color("green"), 10))
		self.font_path = resource_path("models/arial.ttf")  # Make sure to include this font file
		if os.path.exists(self.font_path):
			self.font = ImageFont.truetype(self.font_path, 40)
		else:
			# Fallback to default font
			self.font = ImageFont.load_default()

	def _init_gaze_model(self):
		"""Initialize the gaze detection model (ONNX or PyTorch)."""
		if self.use_onnx:
			import onnxruntime as ort

			# Create session options for better efficiency
			session_options = ort.SessionOptions()
			session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
			session_options.intra_op_num_threads = 2  # Adjust for your hardware

			# Create inference session
			provider = ['CoreMLExecutionProvider']
			self.ort_session = ort.InferenceSession(
				self.gaze_model_path,
				providers=provider,
				sess_options=session_options
			)
			self.input_name = self.ort_session.get_inputs()[0].name

	def detect(self, frame: np.ndarray) -> Tuple[int, List[Tuple[int, int, int, int]], np.ndarray]:
		"""Detect faces and determine if they're looking at the screen."""
		# Increment frame counter
		self.frame_count += 1

		# Step 1: Run face detection on a more frequent schedule
		should_run_face_detection = (self.frame_count % self.face_frame_skip == 0)
		should_run_gaze_detection = (self.frame_count % self.gaze_frame_skip == 0)

		if should_run_face_detection:
			# Run YuNet face detection
			h, w = frame.shape[:2]
			scale_factor = self.target_size / max(h, w)
			new_w = int(w * scale_factor)
			new_h = int(h * scale_factor)
			resized = cv2.resize(frame, (new_w, new_h))

			# Run face detection
			self.detector.setInputSize([new_w, new_h])
			detections = self.detector.infer(resized)

			# Process detections
			if detections.shape[0] > 0:
				# Scale factor to convert back to original size
				inverse_scale = 1.0 / scale_factor

				# For visualization, create a compatible detection result format
				detection_result = self._prepare_visualization_data(detections, frame, inverse_scale)

				# Extract bounding boxes
				new_bboxes = []
				face_bboxes_format = []  # Format for gaze model: [left, top, right, bottom]

				for det in detections:
					if det[-1] >= self.confidence_threshold:  # Check confidence
						# Scale back to original coordinates
						x = int(det[0] * inverse_scale)
						y = int(det[1] * inverse_scale)
						width = int(det[2] * inverse_scale)
						height = int(det[3] * inverse_scale)

						# Convert to [left, top, right, bottom] format for gaze model
						left = max(0, int(x - width * 0.2))
						right = min(w, int(x + width + width * 0.2))
						top = max(0, int(y - height * 0.2))
						bottom = min(h, int(y + height + height * 0.2))

						# Store both formats
						new_bboxes.append((x, y, width, height))
						face_bboxes_format.append([left, top, right, bottom])

				# Update current bboxes
				self.current_bboxes = new_bboxes

				# Step 2: If it's time, also run gaze detection
				if should_run_gaze_detection and new_bboxes:
					# Reset scores for new detection
					self.current_scores = []
					self.looking_bboxes = []

					# Convert frame for PIL
					frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
					frame_pil = Image.fromarray(frame_rgb)

					# Process each face with gaze model
					for i, bbox in enumerate(face_bboxes_format):
						try:
							# Extract face region
							face = frame_pil.crop((bbox))

							# Get gaze score
							score = self._detect_gaze(face)
							self.current_scores.append(score)

							# If score is above threshold, add to looking faces
							if score >= self.gaze_threshold:
								self.looking_bboxes.append(new_bboxes[i])

						except Exception as e:
							print(f"Error processing face for gaze: {e}")
							self.current_scores.append(0.5)  # Default score if processing fails

				# If we updated faces but didn't run gaze detection, we need to adjust scores array
				elif new_bboxes:
					# If number of faces changed, reset scores
					if len(new_bboxes) != len(self.current_scores):
						self.current_scores = [0.5] * len(new_bboxes)
						self.looking_bboxes = []
			else:
				# No faces found
				self.current_bboxes = []
				self.current_scores = []
				self.looking_bboxes = []

				# Create empty detection result for visualization
				detection_result = type('', (), {'detections': []})()

				# Return immediately with no faces
				annotated_frame = self._visualize(frame, detection_result)
				return 0, [], annotated_frame

		# Create annotated frame with current bboxes and scores
		annotated_frame = self._visualize_gaze(frame, self.current_bboxes, self.current_scores)

		return len(self.looking_bboxes), self.looking_bboxes, annotated_frame

	def _detect_gaze(self, face_image: Image.Image):
		"""
		Detect if a face is looking at the screen.

		Args:
			face_image: PIL Image containing a face

		Returns:
			Float score (0-1) indicating probability of looking at screen
		"""
		# Apply transformations
		#img = self.transform(face_image)
		# Convert PIL Image to a ndarray
		img_bgr = cv2.cvtColor(np.array(face_image), cv2.COLOR_RGB2BGR)
		img = preprocess(img_bgr)
		img = np.expand_dims(img, axis=0).astype(np.float32)

		# Run inference
		if self.use_onnx:
			# ONNX inference
			# img_np = img.numpy()
			outputs = self.ort_session.run(None, {self.input_name: img})
			output = outputs[0]

			# Apply sigmoid for final score
			score = 1.0 / (1.0 + np.exp(-output.item()))

		return score

	# TODO: Combine _visualise and _visualise gaze if both get called
	def _visualize_gaze(self, frame, bboxes, scores):
		"""
		Create visualization with gaze information that matches YuNet's style.

		Args:
			frame: Original input frame
			bboxes: List of face bounding boxes (x, y, width, height)
			scores: List of gaze scores

		Returns:
			Frame with visualization
		"""
		# Constants for visualization (match YuNet)
		MARGIN = 25  # pixels
		ROW_SIZE = 25  # pixels
		FONT_SIZE = 3
		FONT_THICKNESS = 5
		FACE_TEXT_COLOR = (255, 0, 0)  # Blue (BGR)

		# Make a copy of the frame for drawing
		annotated_image = frame.copy()

		# Draw each face with gaze score
		for i, bbox in enumerate(bboxes):
			if i < len(scores):
				x, y, w, h = bbox
				score = scores[i]

				# Determine color based on score and threshold
				# Green: definitely not looking (score < threshold - 0.15)
				# Orange: maybe looking (threshold - 0.15 <= score < threshold)
				# Red: definitely looking (score >= threshold)
				
				if score >= self.gaze_threshold:
					# Red - definitely looking at screen
					box_color = (0, 0, 255)  # BGR format
				elif score >= self.gaze_threshold - 0.15:
					# Orange - maybe looking
					box_color = (0, 165, 255)  # BGR format for orange
				else:
					# Green - not looking
					box_color = (0, 255, 0)  # BGR format

				# Draw rectangle with OpenCV (not PIL)
				start_point = (x, y)
				end_point = (x + w, y + h)
				cv2.rectangle(annotated_image, start_point, end_point, box_color, 3)

				# Add text with gaze score (same format as YuNet)
				gaze_text = f"Looking: {score:.2f}"
				# Place the text at the top of the box (like YuNet)
				text_location = (MARGIN + x, MARGIN + ROW_SIZE + y)
				cv2.putText(annotated_image, gaze_text, text_location,
							cv2.FONT_HERSHEY_PLAIN, FONT_SIZE, FACE_TEXT_COLOR, FONT_THICKNESS)

		return annotated_image

	def _drawrect(self, drawcontext, xy, outline=None, width=0):
		"""Helper to draw a rectangle with specified line width."""
		(x1, y1), (x2, y2) = xy
		points = (x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)
		drawcontext.line(points, fill=outline, width=width)

	def _prepare_visualization_data(self, detections, frame, inverse_scale):
		"""
		Prepare detection data in a format compatible with the visualization method.
		This matches the method from YuNetDetector for consistency.
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
		This matches the method from YuNetDetector for consistency.
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
		This matches the method from YuNetDetector for consistency.
		"""
		# Constants for visualization
		MARGIN = 25  # pixels
		ROW_SIZE = 25  # pixels
		FONT_SIZE = 3
		FONT_THICKNESS = 5
		TEXT_COLOR = (255, 0, 0)  # Blue (BGR)

		annotated_image = image.copy()
		height, width, _ = image.shape

		for detection in detection_result.detections:
			# Draw bounding_box
			bbox = detection.bounding_box
			start_point = bbox.origin_x, bbox.origin_y
			end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
			cv2.rectangle(annotated_image, start_point, end_point, TEXT_COLOR, 3)

			# Draw keypoints
			for keypoint in detection.keypoints:
				keypoint_px = self._normalized_to_pixel_coordinates(keypoint.x, keypoint.y, width, height)
				if keypoint_px:
					color, thickness, radius = (0, 255, 0), 10, 2
					cv2.circle(annotated_image, keypoint_px, radius, color, thickness)

			# Draw label and confidence score
			category = detection.categories[0]
			probability = round(category.score, 2)
			result_text = f"Face: {probability:.2f}"
			text_location = (MARGIN + bbox.origin_x, MARGIN + ROW_SIZE + bbox.origin_y)
			cv2.putText(annotated_image, result_text, text_location,
						cv2.FONT_HERSHEY_PLAIN, FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)

		return annotated_image