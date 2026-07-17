"""Text detection (Lab 10 — deep learning) + classical post-processing.

Architecture of the detection stage
-----------------------------------
Per the project's PDI constraints, *text localization* is the one stage that
is allowed to use a learned model. We reuse the same detector mokuro uses
(`comic-text-detector`, a DBNet/YOLO text detector trained on manga), because
classical blob/CC analysis cannot tell text ink from artwork ink — exactly the
failure that a purely classical pipeline hits on real pages.

However, classical PDI is *not* absent from this stage:

  * Pre-processing (``preprocess``): grayscale, CLAHE, denoise, Otsu binarize
    — Labs 02/06/07 — are applied to the page and used to build a debug view
    and to drive the classical post-processing below.
  * Post-processing (this module): the detector returns text *blocks* (one per
    speech bubble / text column). Each block is bigger than what manga-ocr
    expects, so we split it into chunks using the detector's *refined text
    mask* and a **classical density-profile cut** (Labs 02/07): we convolve the
    column-wise ink density with a Gaussian window and cut at the local minima
    (the gaps between characters/lines). This is the same idea mokuro uses, but
    implemented here with plain OpenCV/NumPy so the classical step is explicit
    and documented.

The result is a list of ``DetectedBlock`` objects, each carrying its bounding
box (original image space), reading direction, and the sliced line crops ready
for OCR.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

# comic-text-detector is a heavy DL dependency; import lazily so the rest of
# the backend (e.g. unit tests on the classical segmentation) does not require
# torch to be importable.
try:  # pragma: no cover - import guard
    from comic_text_detector.inference import TextDetector
    from comic_text_detector.utils.textmask import (
        REFINEMASK_INPAINT,
        refine_mask,
    )
    _HAS_DETECTOR = True
except Exception:  # pragma: no cover
    TextDetector = None  # type: ignore
    REFINEMASK_INPAINT = 0  # type: ignore
    refine_mask = None  # type: ignore
    _HAS_DETECTOR = False


DEFAULT_MODEL = os.environ.get(
    "COMIC_TEXT_DETECTOR_MODEL",
    str(Path.home() / ".cache" / "manga-ocr" / "comictextdetector.pt"),
)

# manga-ocr is trained on crops ~ height 64px; chunks beyond this aspect ratio
# are split so each OCR call stays within the model's expected proportions.
TEXT_HEIGHT = 64
MAX_RATIO_VERT = 16
MAX_RATIO_HOR = 8
ANCHOR_WINDOW = 2


@dataclass
class DetectedBlock:
    """A detected text block in original image coordinates."""
    id: int
    x: int
    y: int
    w: int
    h: int
    vertical: bool
    font_size: int
    # OCR-ready crops (BGR uint8), already rotated to horizontal for vertical
    # blocks. One crop per chunk (a block may be split into several).
    crops: List[np.ndarray] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.crops is None:
            self.crops = []

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "x": int(self.x),
            "y": int(self.y),
            "w": int(self.w),
            "h": int(self.h),
            "vertical": bool(self.vertical),
        }


class _Detector:
    """Thin singleton wrapper around comic-text-detector's TextDetector."""

    def __init__(self, model_path: str = DEFAULT_MODEL, device: str = "cpu") -> None:
        if not _HAS_DETECTOR:
            raise RuntimeError(
                "comic-text-detector is not installed; detection unavailable."
            )
        self.model_path = model_path
        self.device = device
        self._det: Optional["TextDetector"] = None

    @property
    def available(self) -> bool:
        return _HAS_DETECTOR and Path(self.model_path).is_file()

    def _ensure(self) -> "TextDetector":
        if self._det is None:
            self._det = TextDetector(
                model_path=self.model_path,
                input_size=1024,
                device=self.device,
                act="leaky",
            )
        return self._det

    def detect(self, img: np.ndarray):
        """Run the detector and return ``(mask, mask_refined, blk_list)``."""
        return self._ensure()(img, refine_mode=REFINEMASK_INPAINT,
                              keep_undetected_mask=True)

    def refine(self, img, mask, blk_list):
        if refine_mask is None:
            return mask
        return refine_mask(img, mask, blk_list, refine_mode=REFINEMASK_INPAINT)


_detector_instance: Optional[_Detector] = None


def get_detector(model_path: str = DEFAULT_MODEL, device: str = "cpu") -> _Detector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _Detector(model_path=model_path, device=device)
    return _detector_instance


# ---------------------------------------------------------------------------
# Classical post-processing: split a block into OCR-sized chunks by ink density
# ---------------------------------------------------------------------------

def _split_block_into_chunks(img: np.ndarray,
                             mask_refined: np.ndarray,
                             blk,
                             line_idx: int,
                             textheight: int = TEXT_HEIGHT,
                             max_ratio: int = MAX_RATIO_VERT,
                             anchor_window: int = ANCHOR_WINDOW) -> List[np.ndarray]:
    """Split one text line/column into OCR-sized chunks.

    Classical density-profile cut (Labs 02/07): we look at the *refined text
    mask* for this line, sum ink along the reading axis to get a density
    profile, smooth it with a Gaussian window, then cut at the deepest local
    minima between characters/lines. Returns a list of BGR crops, rotated to
    horizontal for vertical text.
    """
    try:
        from scipy.signal.windows import gaussian
    except Exception:  # pragma: no cover - scipy may be absent
        def gaussian(M, std):  # minimal fallback
            n = np.arange(0, M) - (M - 1) / 2
            return np.exp(-(n ** 2) / (2 * (std ** 2)))

    line_crop = blk.get_transformed_region(img, line_idx, textheight)
    h, w, *_ = line_crop.shape
    ratio = w / h
    if ratio <= max_ratio:
        return [line_crop]

    k = gaussian(textheight * 2, textheight / 8)
    line_mask = blk.get_transformed_region(mask_refined, line_idx, textheight)
    if line_mask.ndim == 3:
        line_mask = cv2.cvtColor(line_mask, cv2.COLOR_BGR2GRAY)
    num_chunks = int(np.ceil(ratio / max_ratio))

    anchors = np.linspace(0, w, num_chunks + 1)[1:-1]
    line_density = line_mask.sum(axis=0).astype(np.float32)
    if line_density.max() > 0:
        line_density = np.convolve(line_density, k, "same")
        line_density /= line_density.max()

    anchor_window *= textheight
    cut_points: List[int] = []
    for anchor in anchors:
        anchor = int(anchor)
        n0 = int(np.clip(anchor - anchor_window // 2, 0, w))
        n1 = int(np.clip(anchor + anchor_window // 2, 0, w))
        if n1 <= n0:
            continue
        p = int(line_density[n0:n1].argmin()) + n0
        cut_points.append(p)

    if not cut_points:
        return [line_crop]
    return [c for c in np.split(line_crop, cut_points, axis=1)]


def detect_blocks(img: np.ndarray,
                  detector: Optional[_Detector] = None,
                  device: str = "cpu") -> List[DetectedBlock]:
    """Detect text blocks on a full-resolution BGR page.

    Returns a list of ``DetectedBlock`` in rough manga reading order
    (top→bottom, right→left). Blocks carry OCR-ready crops.
    """
    if detector is None:
        detector = get_detector(device=device)
    if not detector.available:
        return []

    mask, mask_refined, blk_list = detector.detect(img)

    out: List[DetectedBlock] = []
    next_id = 0
    for blk in blk_list:
        vertical = bool(getattr(blk, "vertical", False))
        font_size = int(getattr(blk, "font_size", 0) or 0)
        x1, y1, x2, y2 = [int(v) for v in blk.xyxy]
        block = DetectedBlock(
            id=next_id, x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1),
            vertical=vertical, font_size=font_size,
        )
        try:
            lines = list(blk.lines_array())
        except Exception:  # pragma: no cover
            lines = []
        max_ratio = MAX_RATIO_VERT if vertical else MAX_RATIO_HOR
        for li in range(len(lines)):
            chunks = _split_block_into_chunks(
                img, mask_refined, blk, li,
                textheight=TEXT_HEIGHT, max_ratio=max_ratio,
                anchor_window=ANCHOR_WINDOW,
            )
            for c in chunks:
                if vertical:
                    c = cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE)
                block.crops.append(c)
        out.append(block)
        next_id += 1

    # Rough reading order: top-to-bottom; right-to-left for vertical-first.
    out.sort(key=lambda b: (b.y, -b.x))
    return out
