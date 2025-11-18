from typing import Tuple, List

import cv2 as cv
import numpy as np

from utils.yunet import YuNet
from utils.eyesoff_model import EyesOffModel

def _preprocess_for_classifier(
    face_bgr: np.ndarray,
    size: int = 224,
    mean=(0.485, 0.456, 0.406),
    std=(0.229, 0.224, 0.225),
) -> np.ndarray:
    """
    Preprocess BGR face image into a normalized CHW float32 tensor
    suitable for the EyesOff ONNX model.
    """
    # Resize
    img = cv.resize(face_bgr, (size, size), interpolation=cv.INTER_LINEAR)
    # BGR -> RGB
    img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    # To float32 0..1
    img = img.astype(np.float32) / 255.0
    # HWC -> CHW
    img = np.transpose(img, (2, 0, 1))
    # Normalize
    mean_arr = np.asarray(mean, dtype=np.float32)[:, None, None]
    std_arr = np.asarray(std, dtype=np.float32)[:, None, None]
    img = (img - mean_arr) / std_arr
    # Add batch dim
    img = np.expand_dims(img, axis=0).astype(np.float32)
    return img


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


class EyesOffDetector:
    """
    Multi-face gaze detector combining YuNet for face detection
    and EyesOffModel (ONNX) for gaze classification.
    """

    def __init__(
        self,
        eyesoff_model_path: str,
        eyesoff_threshold: float,
        yunet_path: str,
        yunet_confidence_threshold: float,
        yunet_nms_threshold: float = 0.3,
        top_k: int = 2500,
        target_size: int = 340,
        use_gpu: bool = False,
        input_size: int = 224,
        bbox_scale: float = 1.6,
        smoothing_window: int = 1,
    ) -> None:
        """
        Args:
            eyesoff_model_path: Path to EyesOff ONNX model.
            eyesoff_threshold: Probability threshold for "LOOKING".
            yunet_path: Path to YuNet face detector model.
            yunet_confidence_threshold: YuNet detection score threshold.
            yunet_nms_threshold: YuNet NMS threshold.
            top_k: Maximum number of face candidates YuNet considers.
            target_size: Size used when resizing input before YuNet.
            use_gpu: Whether to enable GPU/CoreML for EyesOff ONNX.
            input_size: EyesOff ONNX model input size (e.g., 224).
            bbox_scale: Factor to enlarge face box for cropping.
            smoothing_window: Smoothing window for EyesOffModel.
        """
        self.confidence_threshold = float(yunet_confidence_threshold)
        self.eyesoff_threshold = float(eyesoff_threshold)
        self.target_size = int(target_size)
        self.face_bbox_scale = float(bbox_scale)

        # YuNet backend/target
        backend_id = cv.dnn.DNN_BACKEND_OPENCV
        target_id = cv.dnn.DNN_TARGET_CPU

        # Initialize YuNet face detector
        self.detector = YuNet(
            modelPath=yunet_path,
            inputSize=[self.target_size, self.target_size],
            confThreshold=self.confidence_threshold,
            nmsThreshold=yunet_nms_threshold,
            topK=top_k,
            backendId=backend_id,
            targetId=target_id,
        )

        # Initialize EyesOff ONNX model
        self.eyesoff = EyesOffModel(
            model_path=eyesoff_model_path,
            input_size=input_size,
            decision_threshold=eyesoff_threshold,
            use_gpu=use_gpu,
            smoothing_window=smoothing_window,
        )

    # ---- Internal helpers ----

    @staticmethod
    def _enlarge_bbox(
        bbox_xywh: np.ndarray,
        img_shape: Tuple[int, int, int],
        scale: float = 1.6,
    ) -> np.ndarray:
        """
        Enlarge a bounding box by a scale factor while staying inside image.
        bbox_xywh: [x, y, w, h]
        """
        x, y, w, h = bbox_xywh.astype(np.float32)
        H, W = img_shape[:2]

        cx = x + w / 2.0
        cy = y + h / 2.0
        new_w = w * scale
        new_h = h * scale

        new_x = max(0, int(round(cx - new_w / 2.0)))
        new_y = max(0, int(round(cy - new_h / 2.0)))
        new_w = int(min(round(new_w), W - new_x))
        new_h = int(min(round(new_h), H - new_y))

        return np.array([new_x, new_y, new_w, new_h], dtype=np.int32)

    @staticmethod
    def _crop(image: np.ndarray, bbox_xywh: np.ndarray) -> np.ndarray:
        x, y, w, h = map(int, bbox_xywh)
        return image[y : y + h, x : x + w]

    def _visualize(
        self,
        image: np.ndarray,
        bboxes: List[Tuple[int, int, int, int]],
        gaze_probs: List[float],
        gaze_states: List[bool],
    ) -> np.ndarray:
        """
        Draw bounding boxes and gaze labels on the image.

        Args:
            image: Input BGR image.
            bboxes: List of [x, y, w, h] in original resolution.
            gaze_probs: List of probabilities for "looking".
            gaze_states: List of bools (True = looking).

        Returns:
            Annotated image.
        """
        annotated_image = image.copy()

        for (x, y, w, h), prob, is_looking in zip(bboxes, gaze_probs, gaze_states):
            # Bounding box
            start_point = (x, y)
            end_point = (x + w, y + h)
            color = (0, 200, 0) if is_looking else (0, 0, 255)  # green / red
            cv.rectangle(annotated_image, start_point, end_point, color, 2)

            # Label
            label = "LOOKING" if is_looking else "NOT LOOKING"
            text = f"{label}: {prob:.2f}"
            # Text position slightly above the box
            text_org = (x, max(0, y - 10))
            cv.putText(
                annotated_image,
                text,
                text_org,
                cv.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv.LINE_AA,
            )

        return annotated_image

    # ---- Public API ----

    def detect(
        self,
        frame: np.ndarray,
    ) -> Tuple[int, List[Tuple[int, int, int, int]], np.ndarray, int]:
        """
        Detect faces and run EyesOff gaze inference on each.

        Args:
            frame: Input BGR image.

        Returns:
            Tuple containing:
                - num_faces (int): number of faces with valid gaze predictions
                - bboxes (List[Tuple[int, int, int, int]]): [x, y, w, h] per face (original coords)
                - annotated_frame (np.ndarray): image with boxes + gaze labels
                - num_looking (int): number of people looking at the camera
        """
        h, w = frame.shape[:2]

        # Resize with aspect ratio preserved (like YuNetDetector)
        scale_factor = self.target_size / max(h, w)
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        resized = cv.resize(frame, (new_w, new_h))

        # YuNet expects current input size
        self.detector.setInputSize([new_w, new_h])
        detections = self.detector.infer(resized)  # shape: [N, 15] or [0, 5]/[0, 15]

        bboxes: List[Tuple[int, int, int, int]] = []
        gaze_probs: List[float] = []
        gaze_states: List[bool] = []

        if detections.shape[0] > 0:
            inverse_scale = 1.0 / scale_factor

            for det in detections:
                # YuNet output format: [x, y, w, h, score, l0x, l0y, ..., l4x, l4y]
                score = float(det[4])

                if score < self.confidence_threshold:
                    continue

                # Scale bbox back to original coordinates
                x = int(det[0] * inverse_scale)
                y = int(det[1] * inverse_scale)
                bw = int(det[2] * inverse_scale)
                bh = int(det[3] * inverse_scale)

                # Clamp to image
                x = max(0, min(x, w - 1))
                y = max(0, min(y, h - 1))
                bw = max(1, min(bw, w - x))
                bh = max(1, min(bh, h - y))

                bbox = np.array([x, y, bw, bh], dtype=np.int32)

                # Enlarge bbox for cropping if desired
                enlarged_bbox = self._enlarge_bbox(bbox, frame.shape, scale=self.face_bbox_scale)
                face_crop = self._crop(frame, enlarged_bbox)

                if face_crop.size == 0:
                    continue

                prob, is_looking = self.eyesoff.predict(face_crop)

                bboxes.append((x, y, bw, bh))
                gaze_probs.append(prob)
                gaze_states.append(is_looking)

        annotated_frame = self._visualize(frame, bboxes, gaze_probs, gaze_states)
        num_faces = len(bboxes)
        num_looking = sum(gaze_states)  # Count how many are looking

        return num_faces, bboxes, annotated_frame, num_looking