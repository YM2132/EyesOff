
from typing import Tuple

import cv2 as cv
import numpy as np
import onnxruntime as ort
from collections import deque

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

class EyesOffModel:
    """
    Thin wrapper over an ONNX gaze classifier.

    Assumes binary classifier with a single logit output per sample.
    """

    def __init__(
        self,
        model_path: str,
        input_size: int = 224,
        decision_threshold: float = 0.5,
        use_gpu: bool = False,
        smoothing_window: int = 1,
    ) -> None:
        """
        Args:
            model_path: Path to the EyesOff ONNX model.
            input_size: Input spatial size (e.g., 224).
            decision_threshold: Probability threshold for "looking".
            use_gpu: Whether to try GPU/CoreML provider; falls back to CPU.
            smoothing_window: Rolling window for probability smoothing
                              (1 = no smoothing).
        """
        self.input_size = int(input_size)
        self.decision_threshold = float(decision_threshold)

        # Optional global smoothing (note: across calls, not per-face).
        self._probs = deque(maxlen=max(1, int(smoothing_window)))

        # Provider setup
        if use_gpu:
            providers = [
                (
                    "CoreMLExecutionProvider",
                    {
                        # Additional CoreML options can go here if needed.
                    },
                ),
                "CPUExecutionProvider",
            ]
        else:
            providers = ["CPUExecutionProvider"]

        # Create ONNX Runtime session
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        print(f"EyesOffModel loaded from: {model_path}")
        print(f"  Input name: {self.input_name}")
        print(f"  Output name: {self.output_name}")
        print(f"  Providers: {self.session.get_providers()}")

    def predict(self, face_bgr: np.ndarray) -> Tuple[float, bool]:
        """
        Run gaze prediction for a single face crop.

        Returns:
            prob (float): probability of "looking".
            is_looking (bool): prob >= decision_threshold
        """
        if face_bgr is None or face_bgr.size == 0:
            return 0.0, False

        x = _preprocess_for_classifier(face_bgr, size=self.input_size)
        outputs = self.session.run([self.output_name], {self.input_name: x})
        logits = outputs[0]

        # Handle different output shapes
        if logits.ndim == 2 and logits.shape[1] == 1:
            logits = logits[:, 0]

        prob = float(_sigmoid(logits[0]))

        # Optional smoothing (global)
        if len(self._probs) == self._probs.maxlen:
            self._probs.popleft()
        self._probs.append(prob)
        smoothed_prob = float(np.mean(self._probs))

        is_looking = smoothed_prob >= self.decision_threshold
        return smoothed_prob, is_looking
