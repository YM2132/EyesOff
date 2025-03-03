import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
from typing import Tuple, Union, List, Optional


class MediapipeDetector:
    """
    Face detection implementation using MediaPipe's face detection models.
    """
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        """
        Initialize the MediaPipe face detector.
        
        Args:
            model_path (str): Path to the MediaPipe face detection model (.tflite file)
            confidence_threshold (float): Minimum confidence threshold for detection (0.0-1.0)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        # Initialize the detector
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=confidence_threshold
        )
        self.detector = vision.FaceDetector.create_from_options(options)

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
        # Convert to MediaPipe Image format
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        
        # Run face detection
        detection_result = self.detector.detect(mp_image)
        
        # Extract bounding boxes and count faces
        bboxes = []
        for detection in detection_result.detections:
            if detection.categories[0].score >= self.confidence_threshold:
                bbox = detection.bounding_box
                bboxes.append((bbox.origin_x, bbox.origin_y, bbox.width, bbox.height))
        
        # Create visualized frame
        annotated_frame = self._visualize(frame, detection_result)
        
        return len(bboxes), bboxes, annotated_frame
    
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
            # Check confidence threshold
            if detection.categories[0].score < self.confidence_threshold:
                continue
                
            # Draw bounding_box
            bbox = detection.bounding_box
            start_point = bbox.origin_x, bbox.origin_y
            end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
            cv2.rectangle(annotated_image, start_point, end_point, TEXT_COLOR, 3)
            
            # Draw keypoints
            for keypoint in detection.keypoints:
                keypoint_px = self._normalized_to_pixel_coordinates(keypoint.x, keypoint.y, width, height)
                if keypoint_px:
                    color, thickness, radius = (0, 255, 0), 2, 2
                    cv2.circle(annotated_image, keypoint_px, radius, color, thickness)
            
            # Draw label and confidence score
            category = detection.categories[0]
            probability = round(category.score, 2)
            result_text = f"Face: {probability:.2f}"
            text_location = (MARGIN + bbox.origin_x, MARGIN + ROW_SIZE + bbox.origin_y)
            cv2.putText(annotated_image, result_text, text_location, 
                        cv2.FONT_HERSHEY_PLAIN, FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)
        
        return annotated_image