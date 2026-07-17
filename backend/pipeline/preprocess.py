"""Pre-processing stage (Labs 00, 03, 04, 09).

Implements:
  - Lab 00: numpy/OpenCV/matplotlib image I/O and array handling.
  - Lab 01: sampling / quantization via resize for DPI control.
  - Lab 03: histogram equalization (CLAHE) for contrast on faded pages.
  - Lab 04: low-pass filtering (Gaussian, median, bilateral) for noise.
  - Lab 09: color handling — produce a binary text mask from color pages so
    that painted backgrounds and dark frames do not bleed into the ink mask.

Every function is pure and unit-tested on its own.
"""
from __future__ import annotations

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Lab 00 — sampling
# ---------------------------------------------------------------------------

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert BGR (or already-gray) image to single-channel uint8.

    Accepts color (HxWx3) or grayscale (HxW) input. The color space is treated
    as BGR because that is what `cv2.imread` returns; the conversion uses the
    standard luminance weights, not just averaging channels.
    """
    if image.ndim == 2:
        return image
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError(f"Esperava imagem 2D ou 3D com 3/4 canais, recebi shape={image.shape}")
    if image.shape[2] == 4:
        image = image[:, :, :3]
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_longest_edge(image: np.ndarray, target: int) -> np.ndarray:
    """Resize so that the longest side equals `target` (Lab 01).

    Never upscales: if the image is already smaller than `target`, it is
    returned unchanged. Aspect ratio is preserved.
    """
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= target:
        return image
    scale = target / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# Lab 03 — contrast
# ---------------------------------------------------------------------------

def clahe_equalize(gray: np.ndarray, clip_limit: float = 2.0,
                   tile_grid: tuple[int, int] = (8, 8)) -> np.ndarray:
    """Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization).

    Better than global equalization for manga pages where lighting and ink
    density vary across the page. Output keeps the original dtype/range.
    """
    if gray.ndim != 2:
        raise ValueError("CLAHE espera imagem em escala de cinza (HxW).")
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    return clahe.apply(gray)


# ---------------------------------------------------------------------------
# Lab 04 — low-pass filtering
# ---------------------------------------------------------------------------

def denoise(gray: np.ndarray, method: str = "bilateral",
            ksize: int = 3) -> np.ndarray:
    """Apply a noise-suppression filter (Lab 04).

    Supported methods:
      - "gaussian":  fast, mild smoothing, blurs edges.
      - "median":    good for salt-and-pepper scan artifacts; preserves edges.
      - "bilateral": edge-preserving; preferred for manga ink lines.
    """
    if gray.ndim != 2:
        raise ValueError("denoise espera imagem em escala de cinza (HxW).")
    method = method.lower()
    if method == "gaussian":
        return cv2.GaussianBlur(gray, (ksize, ksize), sigmaX=0)
    if method == "median":
        k = max(3, ksize | 1)  # odd
        return cv2.medianBlur(gray, k)
    if method == "bilateral":
        # d=ksize*2 is the typical default; tune to taste.
        return cv2.bilateralFilter(gray, d=max(3, ksize * 2),
                                   sigmaColor=75, sigmaSpace=75)
    raise ValueError(f"metodo de denoise desconhecido: {method!r}")


# ---------------------------------------------------------------------------
# Lab 09 — color handling: ink vs. paper mask
# ---------------------------------------------------------------------------

def color_to_text_mask(image: np.ndarray,
                       sat_threshold: int = 60,
                       val_threshold: int = 80) -> np.ndarray:
    """Produce a binary mask where ink is white on a black background.

    Strategy (Lab 09):
      1. Convert BGR → HSV.
      2. Drop pixels that are highly saturated (painted/colored areas are
         usually not text in manga).
      3. Drop pixels that are too bright (paper / white).
      4. The remainder is the ink mask.
    """
    if image.ndim == 2:
        # Already gray — keep dark pixels.
        mask = (image < val_threshold).astype(np.uint8) * 255
        return mask
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError(f"Esperava imagem 2D ou 3D, recebi shape={image.shape}")
    if image.shape[2] == 4:
        image = image[:, :, :3]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # Ink: low saturation (mostly black on white) and dark (low value).
    ink = ((sat < sat_threshold) & (val < val_threshold)).astype(np.uint8) * 255
    return ink


# ---------------------------------------------------------------------------
# Top-level: full page pre-processing
# ---------------------------------------------------------------------------

def preprocess_page(image: np.ndarray, target_longest: int = 1600,
                    denoise_method: str = "bilateral",
                    apply_clahe: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Run the full pre-processing pipeline on a single manga page.

    Returns
    -------
    gray : np.ndarray
        Grayscale image resized so the longest side equals `target_longest`.
    mask : np.ndarray
        Binary ink mask on the **original** image scale. Keeping the mask at
        the original resolution makes it easy to map bounding boxes back to
        pixel coordinates without bookkeeping.
    """
    if image.ndim not in (2, 3):
        raise ValueError(f"shape invalido para preprocess_page: {image.shape}")
    mask = color_to_text_mask(image)
    gray = to_grayscale(image)
    if apply_clahe:
        gray = clahe_equalize(gray)
    gray = denoise(gray, method=denoise_method)
    gray = resize_longest_edge(gray, target_longest)
    return gray, mask
