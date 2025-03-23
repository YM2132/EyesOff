from typing import Tuple, List, Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


def cv_to_qimage(cv_img: np.ndarray) -> QImage:
    """
    Convert an OpenCV image to a QImage.
    
    Args:
        cv_img: OpenCV image (numpy array)
        
    Returns:
        QImage: Qt image
    """
    # Convert the color format if needed (OpenCV uses BGR, Qt uses RGB)
    if len(cv_img.shape) == 3 and cv_img.shape[2] == 3:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    
    height, width = cv_img.shape[:2]
    
    # Create QImage based on format
    if len(cv_img.shape) == 2:  # Grayscale
        bytes_per_line = width
        return QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    else:  # Color
        bytes_per_line = 3 * width
        return QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888)


def cv_to_pixmap(cv_img: np.ndarray) -> QPixmap:
    """
    Convert an OpenCV image to a QPixmap.
    
    Args:
        cv_img: OpenCV image (numpy array)
        
    Returns:
        QPixmap: Qt pixmap
    """
    return QPixmap.fromImage(cv_to_qimage(cv_img))


def apply_privacy_blur(frame: np.ndarray, bboxes: List[Tuple[int, int, int, int]], blur_level: int = 20) -> np.ndarray:
    """
    Apply blur to faces in the frame for privacy.
    
    Args:
        frame: Input frame
        bboxes: List of bounding boxes (x, y, width, height)
        blur_level: Level of blur to apply
        
    Returns:
        np.ndarray: Frame with blurred faces
    """
    output = frame.copy()
    
    for (x, y, w, h) in bboxes:
        # Extract the face region
        face_region = output[y:y+h, x:x+w]
        
        # Apply blur
        blurred_face = cv2.GaussianBlur(face_region, (blur_level, blur_level), 0)
        
        # Replace with blurred version
        output[y:y+h, x:x+w] = blurred_face
    
    return output


def apply_pixelation(frame: np.ndarray, bboxes: List[Tuple[int, int, int, int]], pixel_size: int = 15) -> np.ndarray:
    """
    Apply pixelation to faces in the frame for privacy.
    
    Args:
        frame: Input frame
        bboxes: List of bounding boxes (x, y, width, height)
        pixel_size: Size of pixelation blocks
        
    Returns:
        np.ndarray: Frame with pixelated faces
    """
    output = frame.copy()
    
    for (x, y, w, h) in bboxes:
        # Extract the face region
        face = output[y:y+h, x:x+w]
        
        # Resize down and back up to create pixelation effect
        if w > 0 and h > 0:  # Check to avoid division by zero
            temp = cv2.resize(face, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # Replace with pixelated version
            output[y:y+h, x:x+w] = pixelated
    
    return output


def draw_detection_info(frame: np.ndarray, num_faces: int, fps: float,
                        threshold: int, alert_active: bool, text_scale: float = 1.0) -> np.ndarray:
    """
    Draw detection information on the frame with appropriate scaling.

    Args:
        frame: Input frame
        num_faces: Number of detected faces
        fps: Current FPS
        threshold: Face threshold for alert
        alert_active: Whether an alert is currently active
        text_scale: Scale factor for text and UI elements (default: 1.0)

    Returns:
        np.ndarray: Frame with information overlaid
    """
    output = frame.copy()
    height, width = output.shape[:2]

    # Scale UI elements based on text_scale
    rect_width = int(250 * text_scale)
    rect_height = int(85 * text_scale)
    border_thickness = max(1, int(1 * text_scale))

    # Background rectangle for text - scaled
    cv2.rectangle(output, (10, 10), (10 + rect_width, 10 + rect_height), (0, 0, 0), -1)
    cv2.rectangle(output, (10, 10), (10 + rect_width, 10 + rect_height), (255, 255, 255), border_thickness)

    # Face count with color based on threshold - scaled
    face_color = (0, 0, 255) if num_faces > threshold else (0, 255, 0)
    font_size_faces = 0.8 * text_scale
    font_thickness_faces = max(1, int(2 * text_scale))
    cv2.putText(output, f"Faces: {num_faces}",
                (int(20 * text_scale), int(40 * text_scale)),
                cv2.FONT_HERSHEY_SIMPLEX, font_size_faces, face_color, font_thickness_faces)

    # FPS counter - scaled
    font_size_fps = 0.6 * text_scale
    font_thickness_fps = max(1, int(1 * text_scale))
    cv2.putText(output, f"FPS: {fps:.1f}",
                (int(20 * text_scale), int(70 * text_scale)),
                cv2.FONT_HERSHEY_SIMPLEX, font_size_fps, (255, 255, 255), font_thickness_fps)

    # Alert indicator - scaled
    # TODO - Alert indicator is not being removed
    if alert_active:
        # Draw a red indicator in the corner
        indicator_radius = int(15 * text_scale)
        indicator_x = width - int(30 * text_scale)
        indicator_y = int(30 * text_scale)

        cv2.circle(output, (indicator_x, indicator_y), indicator_radius, (0, 0, 255), -1)
        cv2.putText(output, "!",
                    (indicator_x - int(4 * text_scale), indicator_y + int(6 * text_scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8 * text_scale, (255, 255, 255),
                    max(1, int(2 * text_scale)))

    return output