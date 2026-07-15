from __future__ import annotations

import cv2
import numpy as np


def sobel(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    dx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    dy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
    mag = cv2.magnitude(dx, dy)
    return cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def laplacian(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
    return cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def canny(gray: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    return cv2.Canny(gray, low, high)
