"""
Inference engine — two modes:

1. **opencv** (default) — rule-based checks using OpenCV contour / edge analysis.
   Detects six defect categories relevant to ignition moulding:
     * ovality       — non-round features (high eccentricity)
     * burr          — small sharp protrusions on edges
     * flash         — thin excess material along parting lines
     * hole_shift    — holes displaced from expected centre
     * crack         — linear fractures / fissures
     * surface_marks — scratches, pitting, texture anomalies

2. **onnx** — placeholder that loads an ONNX model and runs a forward pass.
   Replace the dummy model path with a real trained model to activate.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List

import cv2
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Defect:
    type: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    score: float = 0.0
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        # Convert numpy types to native Python for JSON serialization
        def _native(v):
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v)
            return v

        return {
            "type": self.type,
            "bbox": [int(self.x), int(self.y), int(self.w), int(self.h)],
            "score": round(float(self.score), 3),
            "meta": {k: _native(v) for k, v in self.meta.items()},
        }


@dataclass
class InferenceResult:
    passed: bool
    defects: List[Defect]
    confidence: float

    @property
    def result_str(self) -> str:
        return "pass" if self.passed else "fail"


# ---------------------------------------------------------------------------
# OpenCV rule-based engine  (6 defect types)
# ---------------------------------------------------------------------------

class OpenCVInspector:
    """
    Rule-based defect detection for moulded ignition parts.

    All thresholds are class-level — override per-instance if needed.
    """

    # --- Ovality ---
    OVALITY_AREA_MIN = 200
    OVALITY_AREA_MAX = 10000
    OVALITY_THRESHOLD = 0.35          # (major-minor)/major of fitted ellipse

    # --- Burr ---
    BURR_AREA_MIN = 30
    BURR_AREA_MAX = 2000
    BURR_SPIKINESS = 250.0            # perimeter^2 / area threshold

    # --- Flash (thin excess material along parting line) ---
    FLASH_ASPECT_RATIO_MIN = 5.0      # very elongated contours
    FLASH_AREA_MIN = 80
    FLASH_AREA_MAX = 4000

    # --- Hole shift ---
    HOLE_AREA_MIN = 100
    HOLE_AREA_MAX = 5000
    HOLE_CIRCULARITY_MIN = 0.60
    HOLE_SHIFT_RATIO = 0.15           # centre offset / image diagonal

    # --- Crack (line-like features via Hough) ---
    CRACK_MIN_LINE_LENGTH = 40
    CRACK_MAX_LINE_GAP = 10
    CRACK_HOU_THRESHOLD = 50

    # --- Surface marks (local texture anomalies) ---
    SURFACE_STDDEV_FACTOR = 1.8       # blocks with std > factor * global std

    def inspect(self, image: np.ndarray) -> InferenceResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape[:2]
        diag = math.sqrt(h_img ** 2 + w_img ** 2)
        img_cx, img_cy = w_img / 2.0, h_img / 2.0

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 4,
        )

        contours, _ = cv2.findContours(
            binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE,
        )

        defects: List[Defect] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 20:
                continue

            perimeter = cv2.arcLength(cnt, True)
            x, y, w, h = cv2.boundingRect(cnt)

            # --- Hole shift: circular contour whose centre is far from image centre ---
            if self.HOLE_AREA_MIN < area < self.HOLE_AREA_MAX and perimeter > 0:
                circularity = 4 * math.pi * area / (perimeter * perimeter)
                if circularity > self.HOLE_CIRCULARITY_MIN:
                    cx, cy = x + w / 2.0, y + h / 2.0
                    offset = math.sqrt((cx - img_cx) ** 2 + (cy - img_cy) ** 2)
                    shift_ratio = offset / diag
                    if shift_ratio > self.HOLE_SHIFT_RATIO:
                        defects.append(Defect(
                            type="hole_shift", x=x, y=y, w=w, h=h,
                            score=round(min(shift_ratio, 1.0), 3),
                            meta={
                                "area": int(area),
                                "circularity": round(circularity, 3),
                                "shift_ratio": round(shift_ratio, 3),
                            },
                        ))
                    continue  # skip further checks for circular shapes

            # --- Ovality: elliptical contour with high eccentricity ---
            if len(cnt) >= 5 and self.OVALITY_AREA_MIN < area < self.OVALITY_AREA_MAX:
                ellipse = cv2.fitEllipse(cnt)
                (_, (ma, MA), _) = ellipse
                if MA > 0:
                    eccentricity = abs(MA - ma) / MA
                    if eccentricity > self.OVALITY_THRESHOLD:
                        defects.append(Defect(
                            type="ovality", x=x, y=y, w=w, h=h,
                            score=round(min(eccentricity, 1.0), 3),
                            meta={"eccentricity": round(eccentricity, 3)},
                        ))
                        continue

            # --- Flash: very elongated thin contour ---
            short_side = min(w, h)
            long_side = max(w, h)
            if (short_side > 0
                    and long_side / short_side > self.FLASH_ASPECT_RATIO_MIN
                    and self.FLASH_AREA_MIN < area < self.FLASH_AREA_MAX):
                aspect = long_side / short_side
                defects.append(Defect(
                    type="flash", x=x, y=y, w=w, h=h,
                    score=round(min(aspect / 20.0, 1.0), 3),
                    meta={"aspect_ratio": round(aspect, 2)},
                ))
                continue

            # --- Burr: small spiky contour ---
            if self.BURR_AREA_MIN < area < self.BURR_AREA_MAX and perimeter > 0:
                spikiness = (perimeter * perimeter) / area
                if spikiness > self.BURR_SPIKINESS:
                    defects.append(Defect(
                        type="burr", x=x, y=y, w=w, h=h,
                        score=round(min(spikiness / 1000.0, 1.0), 3),
                        meta={"spikiness": round(spikiness, 1)},
                    ))

        # --- Crack detection (Hough line transform on edge map) ---
        edges = cv2.Canny(blurred, 50, 150)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.CRACK_HOU_THRESHOLD,
            minLineLength=self.CRACK_MIN_LINE_LENGTH,
            maxLineGap=self.CRACK_MAX_LINE_GAP,
        )
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                bx = min(x1, x2)
                by = min(y1, y2)
                bw = abs(x2 - x1)
                bh = abs(y2 - y1)
                defects.append(Defect(
                    type="crack", x=bx, y=by, w=bw, h=bh,
                    score=round(min(length / diag, 1.0), 3),
                    meta={"length_px": round(length, 1)},
                ))

        # --- Surface marks: blocks with abnormally high local std-dev ---
        block_size = 32
        global_std = float(np.std(gray))
        threshold_std = global_std * self.SURFACE_STDDEV_FACTOR
        for by in range(0, h_img - block_size, block_size):
            for bx in range(0, w_img - block_size, block_size):
                block = gray[by:by + block_size, bx:bx + block_size]
                local_std = float(np.std(block))
                if local_std > threshold_std and local_std > 15:
                    defects.append(Defect(
                        type="surface_marks",
                        x=bx, y=by, w=block_size, h=block_size,
                        score=round(min(local_std / 128.0, 1.0), 3),
                        meta={"local_std": round(local_std, 2),
                               "global_std": round(global_std, 2)},
                    ))

        passed = len(defects) == 0
        confidence = 1.0 if passed else max(d.score for d in defects)
        return InferenceResult(passed=passed, defects=defects, confidence=confidence)


# ---------------------------------------------------------------------------
# ONNX placeholder engine
# ---------------------------------------------------------------------------

class ONNXInspector:
    """
    Placeholder ONNX inference.

    To use a real model:
      1.  Export your PyTorch / TF model to ONNX.
      2.  Set ONNX_MODEL_PATH in .env.
      3.  Adjust `_preprocess` and `_postprocess` for your model's I/O.
    """

    def __init__(self, model_path: str):
        if ort is None:
            raise RuntimeError("onnxruntime is not installed")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"ONNX model not found at {model_path}. "
                "Place your model there or switch INFERENCE_MODE to 'opencv'."
            )
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name

    def inspect(self, image: np.ndarray) -> InferenceResult:
        tensor = self._preprocess(image)
        outputs = self.session.run(None, {self.input_name: tensor})
        return self._postprocess(outputs)

    @staticmethod
    def _preprocess(image: np.ndarray) -> np.ndarray:
        """Resize + normalise to NCHW float32 — adjust for your model."""
        img = cv2.resize(image, (224, 224))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))     # HWC -> CHW
        return np.expand_dims(img, axis=0)      # add batch dim

    @staticmethod
    def _postprocess(outputs: list) -> InferenceResult:
        """
        Placeholder postprocess — adjust for your actual model output.
        """
        scores = outputs[0][0]
        predicted = int(np.argmax(scores))

        defect_names = {
            1: "ovality", 2: "burr", 3: "flash",
            4: "hole_shift", 5: "crack", 6: "surface_marks",
        }

        if predicted == 0:
            return InferenceResult(passed=True, defects=[], confidence=float(scores[0]))

        defect_type = defect_names.get(predicted, "unknown")
        return InferenceResult(
            passed=False,
            defects=[Defect(type=defect_type, score=float(scores[predicted]))],
            confidence=float(scores[predicted]),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_inspector(mode: str = "opencv", model_path: str = ""):
    if mode == "onnx":
        return ONNXInspector(model_path)
    return OpenCVInspector()
