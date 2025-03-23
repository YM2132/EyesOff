from typing import Tuple, List, Dict, Any, Optional

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

# Import the existing detector implementations
# from mediapipe_detector import MediapipeDetector
from yunet_detector import YuNetDetector


class FaceDetectorSignals(QObject):
    """Signals for the face detector."""
    # Signal emitted when detection results are ready
    detection_ready = pyqtSignal(int, list, np.ndarray)
    # Signal emitted when an error occurs
    error_occurred = pyqtSignal(str)


class FaceDetector:
    """
    Face detector with PyQt signal integration.
    """
    
    def __init__(self, detector_type: str, model_path: str, confidence_threshold: float = 0.5):
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

    def detect(self, frame: np.ndarray) -> Tuple[int, List[Tuple[int, int, int, int]], np.ndarray]:
        """
        Detect faces in the given frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            Tuple containing:
                - Number of faces detected
                - List of bounding boxes [x, y, width, height]
                - Annotated frame with visualizations
        """
        try:
            if self.detector is None:
                self._create_detector()
                
            # Perform detection
            num_faces, bboxes, annotated_frame = self.detector.detect(frame)
            
            # Emit signal with results
            self.signals.detection_ready.emit(num_faces, bboxes, annotated_frame)
            
            return num_faces, bboxes, annotated_frame
            
        except Exception as e:
            self.signals.error_occurred.emit(f"Detection error: {e}")
            return 0, [], frame
    
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
                "./models/face_detection_yunet_2023mar.onnx"
            ],
            # Additional detector types can be added here in the future
            # Example:
            # "new_detector": [
            #    "/path/to/model1.model",
            #    "/path/to/model2.model"
            # ]
        }