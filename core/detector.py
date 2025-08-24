from typing import Tuple, List, Dict, Any, Optional

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

# Import the existing detector implementations
# from mediapipe_detector import MediapipeDetector
from yunet_detector import YuNetDetector

from utils.resource_path import resource_path


class FaceDetectorSignals(QObject):
    """Signals for the face detector."""
    # Signal emitted when detection results are ready
    detection_ready = pyqtSignal(int, list, np.ndarray, int)
    # Signal emitted when an error occurs
    error_occurred = pyqtSignal(str)


class FaceDetector:
    """
    Face detector with PyQt signal integration.
    """
    
    def __init__(self, detector_type: str, model_path: str, confidence_threshold: float = 0.5,
                 gaze_model_path: str = None, gaze_threshold: float = 0.4):
        """
        Initialize the face detector.
        
        Args:
            detector_type: Type of detector ('yunet')
            model_path: Path to the detector model file
            confidence_threshold: Minimum confidence for detection
        """
        self.detector_type = detector_type
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.detector = None
        self.signals = FaceDetectorSignals()

        # Gaze detection settings
        self.gaze_model_path = gaze_model_path
        self.gaze_threshold = gaze_threshold
        
        # Create the appropriate detector
        self._create_detector()
    
    def _create_detector(self):
        """Create the appropriate detector based on the type."""
        try:
            if self.detector_type.lower() == 'yunet':
                self.detector = YuNetDetector(self.model_path, self.confidence_threshold)
            else:
                raise ValueError(f"Unsupported detector type: {self.detector_type}")
        except Exception as e:
            self.signals.error_occurred.emit(f"Error creating detector: {e}")

    def detect(self, frame: np.ndarray) -> Tuple[int, List[Tuple[int, int, int, int]], np.ndarray, int]:
        """
        Detect faces in the given frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            Tuple containing:
                - Number of faces detected
                - List of bounding boxes [x, y, width, height]
                - Annotated frame with visualizations
                - Number of people looking (0 for non-gaze based methods)
        """
        try:
            if self.detector is None:
                self._create_detector()
                
            # Perform detection
            num_faces, bboxes, annotated_frame, num_looking = self.detector.detect(frame)
            
            # Emit signal with results
            self.signals.detection_ready.emit(num_faces, bboxes, annotated_frame, num_looking)
            
            return num_faces, bboxes, annotated_frame, num_looking
            
        except Exception as e:
            self.signals.error_occurred.emit(f"Detection error: {e}")
            return 0, [], frame, 0
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update detector settings.
        
        Args:
            settings: Dictionary of settings to update
            
        Returns:
            bool: True if updated successfully
        """
        try:
            if 'detector_type' in settings and settings['detector_type'] != self.detector_type:
                self.detector_type = settings['detector_type']
                # Need to recreate detector if type changed
                recreate = True
            else:
                recreate = False
                
            if 'model_path' in settings and settings['model_path'] != self.model_path:
                self.model_path = settings['model_path']
                recreate = True

            if 'confidence_threshold' in settings and settings['confidence_threshold'] != self.confidence_threshold:
                self.confidence_threshold = settings['confidence_threshold']
                recreate = True

            if 'gaze_threshold' in settings:
                self.gaze_threshold = settings["gaze_threshold"]
                if hasattr(self.detector, "gaze_threshold"):
                    # Only update if the detector is a gaze detector with this property
                    self.detector.gaze_threshold = self.gaze_threshold

            if recreate:
                self._create_detector()
                
            return True
            
        except Exception as e:
            self.signals.error_occurred.emit(f"Error updating detector settings: {e}")
            return False
            
    @staticmethod
    def get_available_models() -> Dict[str, List[str]]:
        """
        Get a list of available detection models.
        
        Returns:
            Dict: Dictionary of detector types and their available models
        """
        # In a real application, this would scan for available models
        # For now, we'll return only the implemented models
        return {
            "yunet": [
                f"{resource_path('models/face_detection_yunet_2023mar.onnx')}"
            ],
            "gaze": [
                f"{resource_path('models/face_detection_yunet_2023mar.onnx')}"
            ]
            # Additional detector types can be added here in the future
            # Example:
            # "new_detector": [
            #    "/path/to/model1.model",
            #    "/path/to/model2.model"
            # ]
        }