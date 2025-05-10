import math
import os
import random
from typing import Tuple, List, Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image, ImageDraw, ImageFont
from colour import Color

from utils.yunet import YuNet
from utils.resource_path import resource_path


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
				 frame_skip: int = 20,
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
		self.frame_skip = frame_skip
		self.use_onnx = use_onnx
		self.frame_count = 0
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
		self.transform = transforms.Compose([
			transforms.Resize(224),
			transforms.CenterCrop(224),
			transforms.ToTensor(),
			transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
		])

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
		"""
		Detect faces and determine if they're looking at the screen.

		Args:
			frame: Input image frame

		Returns:
			Tuple containing:
				- Number of faces looking at the screen
				- List of looking faces' bounding boxes [x, y, width, height]
				- Annotated frame with gaze visualizations
		"""
		# Increment frame counter
		self.frame_count += 1

		# Process frame conditionally to improve performance
		should_process = (self.frame_count % self.frame_skip == 0)

		# print('RUNNING DETECTION')

		# print(f'should_process: {should_process}')
		# print(f'frame count: {self.frame_count}')

		if should_process:
			# First detect faces with YuNet
			h, w = frame.shape[:2]
			scale_factor = self.target_size / max(h, w)
			new_w = int(w * scale_factor)
			new_h = int(h * scale_factor)
			resized = cv2.resize(frame, (new_w, new_h))

			# Run face detection
			self.detector.setInputSize([new_w, new_h])
			detections = self.detector.infer(resized)

			# Prepare variables for results
			bboxes = []
			face_bboxes_format = []  # Format for the gaze model: [left, top, right, bottom]
			gaze_scores = []

			# Process detections
			if detections.shape[0] > 0:
				# Scale factor to convert back to original size
				inverse_scale = 1.0 / scale_factor

				# For visualization, create a compatible detection result format
				detection_result = self._prepare_visualization_data(detections, frame, inverse_scale)

				# Process each face detection
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
						bboxes.append((x, y, width, height))
						face_bboxes_format.append([left, top, right, bottom])

				# Process faces with gaze model if faces were detected
				if face_bboxes_format:
					# Prepare image for PIL processing
					frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
					frame_pil = Image.fromarray(frame_rgb)

					looking_bboxes = []

					# Process each face
					for i, bbox in enumerate(face_bboxes_format):
						try:
							# Extract face region
							face = frame_pil.crop((bbox))

							# Get gaze score
							score = self._detect_gaze(face)
							gaze_scores.append(score)

							# If score is above threshold, add to looking faces
							if score >= self.gaze_threshold:
								looking_bboxes.append(bboxes[i])

						except Exception as e:
							print(f"Error processing face for gaze: {e}")
							gaze_scores.append(0.5)  # Default score if processing fails

					# Create annotated frame
					annotated_frame = self._visualize_gaze(frame, face_bboxes_format, gaze_scores)

					# Store results for future frames
					self.last_bboxes = bboxes.copy()
					self.last_scores = gaze_scores.copy()
					self.last_looking_bboxes = looking_bboxes.copy()

					return len(looking_bboxes), looking_bboxes, annotated_frame

			# Empty detection result - no faces found
			self.last_bboxes = []
			self.last_scores = []
			self.last_looking_bboxes = []

			# Create empty detection result for visualization
			detection_result = type('', (), {'detections': []})()

			# For consistency with YuNetDetector
			annotated_frame = self._visualize(frame, detection_result)

			return 0, [], annotated_frame

		else:
			# Use cached results from last processed frame
			frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			frame_pil = Image.fromarray(frame_rgb)

			# Convert to face_bboxes_format for visualization
			face_bboxes_format = []
			for bbox in self.last_bboxes:
				x, y, w, h = bbox
				left = max(0, int(x - w * 0.2))
				right = min(frame.shape[1], int(x + w + w * 0.2))
				top = max(0, int(y - h * 0.2))
				bottom = min(frame.shape[0], int(y + h + h * 0.2))
				face_bboxes_format.append([left, top, right, bottom])

			# Create annotated frame using cached results
			annotated_frame = self._visualize_gaze(frame, face_bboxes_format, self.last_scores)

			return len(self.last_looking_bboxes), self.last_looking_bboxes, annotated_frame

	def _detect_gaze(self, face_image):
		"""
		Detect if a face is looking at the screen.

		Args:
			face_image: PIL Image containing a face

		Returns:
			Float score (0-1) indicating probability of looking at screen
		"""
		# Apply transformations
		img = self.transform(face_image)
		img.unsqueeze_(0)  # Add batch dimension

		# Run inference
		if self.use_onnx:
			# ONNX inference
			img_np = img.numpy()
			outputs = self.ort_session.run(None, {self.input_name: img_np})
			output = outputs[0]

			# Apply sigmoid for final score
			score = 1.0 / (1.0 + np.exp(-output.item()))
		else:
			# PyTorch inference
			img = img.to(self.device)
			with torch.no_grad():
				output = self.torch_model(img)
			score = F.sigmoid(output).item()

		return score

	def _visualize_gaze(self, frame, bboxes, scores):
		"""
		Create visualization with gaze information.

		Args:
			frame: Original input frame
			bboxes: List of face bounding boxes [left, top, right, bottom]
			scores: List of gaze scores

		Returns:
			Frame with visualization
		"""
		# Convert to PIL for drawing
		frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		frame_pil = Image.fromarray(frame_rgb)
		draw = ImageDraw.Draw(frame_pil)

		# Draw each face with gaze score
		for i, bbox in enumerate(bboxes):
			if i < len(scores):
				score = scores[i]

				# Determine color based on score (red to green)
				coloridx = 9 - min(int(round(score * 10)), 9)

				# Draw rectangle with color based on score
				self._drawrect(draw, [(bbox[0], bbox[1]), (bbox[2], bbox[3])],
							   outline=self.colors[coloridx].hex, width=5)

				# Add text with score
				label = f"Looking: {score:.2f}"
				draw.text((bbox[0], bbox[3]), label, fill=(255, 255, 255, 128), font=self.font)

		# Convert back to OpenCV
		result = np.array(frame_pil)
		result = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

		return result

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