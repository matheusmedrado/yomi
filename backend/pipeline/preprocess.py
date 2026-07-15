from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img.copy()
    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def resize_longest_edge(img: np.ndarray, target: int) -> np.ndarray:
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= target:
        return img.copy()
    scale = target / float(longest)
    new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(img, new_size, interpolation=interpolation)


def clahe_equalize(gray: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(gray)


def denoise(gray: np.ndarray, method: str = "gaussian", kernel_size: int = 3) -> np.ndarray:
    k = max(3, kernel_size if kernel_size % 2 == 1 else kernel_size + 1)
    if method == "median":
        return cv2.medianBlur(gray, k)
    if method == "bilateral":
        return cv2.bilateralFilter(gray, k, 75, 75)
    return cv2.GaussianBlur(gray, (k, k), 0)


def color_to_text_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = to_grayscale(img)
    low_sat = hsv[:, :, 1] < 40
    low_val = hsv[:, :, 2] < 200
    paper_like = np.logical_and(low_sat, low_val)
    text_candidate = gray < 128
    return np.logical_and(text_candidate, paper_like).astype(np.uint8) * 255


def preprocess_page(
    img: np.ndarray,
    target_longest: int = 1600,
    use_clahe: bool = True,
    denoise_method: str = "gaussian",
    denoise_kernel: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    gray = to_grayscale(img)
    gray = resize_longest_edge(gray, target_longest)
    if use_clahe:
        gray = clahe_equalize(gray)
    gray = denoise(gray, method=denoise_method, kernel_size=denoise_kernel)
    return gray, color_to_text_mask(img)
