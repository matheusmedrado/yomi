"""Edge-detection stage (Lab 05).

Provides the three classical edge operators that show up in the course:
Sobel (gradient magnitude), Laplacian (second-order derivative) and Canny
(gradient + non-maximum suppression + hysteresis). All return uint8 images
with the same shape as the input.
"""
from __future__ import annotations

import cv2
import numpy as np


def sobel(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Sobel gradient magnitude, normalized to uint8."""
    if gray.ndim != 2:
        raise ValueError("sobel espera imagem em escala de cinza (HxW).")
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=ksize)
    mag = cv2.magnitude(gx, gy)
    mag = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return mag.astype(np.uint8)


def laplacian(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Laplacian (second-order) edges, normalized to uint8."""
    if gray.ndim != 2:
        raise ValueError("laplacian espera imagem em escala de cinza (HxW).")
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=ksize)
    lap = cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX)
    return lap.astype(np.uint8)


def canny(gray: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    """Canny edges. Output is binary (only 0/255 values)."""
    if gray.ndim != 2:
        raise ValueError("canny espera imagem em escala de cinza (HxW).")
    return cv2.Canny(gray, low, high)
