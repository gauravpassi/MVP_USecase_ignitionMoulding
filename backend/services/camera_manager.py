"""
Camera manager — handles USB webcams and RTSP IP cameras.

Each camera gets an OpenCV VideoCapture that is opened on-demand and
cached so repeated snapshot calls don't re-open the stream.
"""
from __future__ import annotations

import threading
import cv2
import numpy as np


class CameraManager:
    """Thread-safe singleton that manages VideoCapture instances."""

    _instance: CameraManager | None = None
    _lock = threading.Lock()

    def __new__(cls) -> CameraManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._captures: dict[str, cv2.VideoCapture] = {}
        return cls._instance

    # ---- public API -------------------------------------------------------

    def open(self, camera_id: str, source_type: str, source_uri: str) -> bool:
        """Open (or re-open) a camera. Returns True on success."""
        self.close(camera_id)
        cap = self._make_capture(source_type, source_uri)
        if cap is None or not cap.isOpened():
            return False
        self._captures[camera_id] = cap
        return True

    def snapshot(
        self,
        camera_id: str,
        source_type: str,
        source_uri: str,
        roi: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray | None:
        """
        Grab a single frame.  Opens the camera lazily if needed.

        roi = (x, y, w, h) — applied after capture.  (0,0,0,0) means full frame.
        """
        cap = self._captures.get(camera_id)
        if cap is None or not cap.isOpened():
            if not self.open(camera_id, source_type, source_uri):
                return None
            cap = self._captures[camera_id]

        ok, frame = cap.read()
        if not ok or frame is None:
            # try re-opening once (RTSP streams may drop)
            self.open(camera_id, source_type, source_uri)
            cap = self._captures.get(camera_id)
            if cap is None:
                return None
            ok, frame = cap.read()
            if not ok or frame is None:
                return None

        if roi and roi[2] > 0 and roi[3] > 0:
            x, y, w, h = roi
            frame = frame[y : y + h, x : x + w]

        return frame

    def close(self, camera_id: str) -> None:
        cap = self._captures.pop(camera_id, None)
        if cap is not None:
            cap.release()

    def close_all(self) -> None:
        for cid in list(self._captures.keys()):
            self.close(cid)

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _make_capture(source_type: str, source_uri: str) -> cv2.VideoCapture | None:
        if source_type == "usb":
            idx = int(source_uri)
            cap = cv2.VideoCapture(idx)
        elif source_type == "rtsp":
            cap = cv2.VideoCapture(source_uri)
        else:
            return None
        return cap


# Module-level convenience instance
camera_manager = CameraManager()
