"""manga-ocr wrapper.

The model is loaded **lazily on first use** so the rest of the app stays
responsive even if the user's first hover comes in cold. We also keep the
input pipeline deliberately simple: a tight BGR crop → BGR→RGB → PIL → model.
A small padding around the crop helps the recognizer with bubble edges.

If `manga-ocr` is not installed (e.g. during the part of development where we
just want the classical pipeline running), `MangaOcrService.recognize` returns
an empty string and logs once. This is what lets the rest of the project
keep working without the heavy DL dependency.
"""
from __future__ import annotations

import io
import logging
import threading
from typing import Optional

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


class MangaOcrService:
    """Lazy singleton around `MangaOcr`."""

    _instance: Optional["MangaOcrService"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._mocr = None
        self._tried_load = False
        self._available: bool | None = None
        # Serializes inference — concurrent PyTorch/MPS calls from Flask's
        # threaded server can crash or corrupt results.
        self._infer_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "MangaOcrService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- public API -----------------------------------------------------

    def warm_up(self) -> bool:
        """Load the model eagerly. Returns True if it loaded successfully."""
        self._ensure_loaded()
        return self._available is True

    def is_available(self) -> bool:
        if self._available is None:
            self._ensure_loaded()
        return self._available is True

    def recognize(self, crop_bgr: np.ndarray, padding: int = 12) -> str:
        """Recognize the Japanese text in a tight crop of a speech bubble.

        `crop_bgr` is an OpenCV-style BGR image. A small white padding is
        added so the model does not see ink touching the edges.
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return ""
        self._ensure_loaded()
        if not self.is_available():
            return ""

        pad = max(0, int(padding))
        if pad > 0:
            crop_bgr = cv2.copyMakeBorder(
                crop_bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT,
                value=(255, 255, 255),
            )
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        import time
        t0 = time.perf_counter()
        try:
            with self._infer_lock:
                text = self._mocr(pil)  # type: ignore[misc]
        except Exception as e:  # noqa: BLE001
            log.exception("manga-ocr recognize failed: %s", e)
            return ""
        dt = (time.perf_counter() - t0) * 1000
        log.info("ocr: %.0fms crop=%dx%d text=%r",
                 dt, crop_bgr.shape[1], crop_bgr.shape[0], (text or "")[:60])
        return (text or "").strip()

    # ---- internals ------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._available is not None:
            return
        with self._lock:
            if self._available is not None:
                return
            self._tried_load = True
            try:
                from manga_ocr import MangaOcr  # type: ignore
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "manga-ocr not installed (%s); OCR will return empty strings.",
                    e,
                )
                self._available = False
                return
            try:
                self._mocr = MangaOcr()
                self._available = True
                log.info("manga-ocr loaded successfully.")
            except Exception as e:  # noqa: BLE001
                log.exception("Failed to initialize manga-ocr: %s", e)
                self._available = False


def encode_crop_for_debug(crop_bgr: np.ndarray) -> bytes:
    """Encode a crop as PNG bytes for the debug endpoints."""
    ok, buf = cv2.imencode(".png", crop_bgr)
    if not ok:
        return b""
    return buf.tobytes()
