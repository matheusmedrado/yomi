from __future__ import annotations

import cv2
import numpy as np


def to_binary(gray: np.ndarray) -> np.ndarray:
    if gray.dtype != np.uint8:
        gray = gray.astype(np.uint8)
    unique = np.unique(gray)
    if unique.size <= 2 and {0, 255}.issuperset(unique.tolist()):
        ink = int(np.count_nonzero(gray))
        if ink > gray.size // 2:
            return cv2.bitwise_not(gray)
        return gray.copy()
    if gray.max() > 1:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        binary = (gray * 255).astype(np.uint8)
    return binary


def crop_to_bbox(binary: np.ndarray) -> np.ndarray | None:
    coords = cv2.findNonZero(binary)
    if coords is None or len(coords) == 0:
        return None
    x, y, w, h = cv2.boundingRect(coords)
    return binary[y : y + h, x : x + w]


def deskew(binary: np.ndarray) -> np.ndarray:
    coords = cv2.findNonZero(binary)
    if coords is None or len(coords) < 10:
        return binary
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    if abs(angle) < 2.0 or abs(angle) > 15.0:
        return binary
    h, w = binary.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(binary, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)


def normalize_glyph(binary: np.ndarray, size: int = 64) -> np.ndarray:
    ink = to_binary(binary)
    cropped = crop_to_bbox(ink)
    if cropped is None:
        return np.zeros((size, size), dtype=np.uint8)

    cropped = deskew(cropped)

    h, w = cropped.shape
    scale = (size - 8) / float(max(h, w))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((size, size), dtype=np.uint8)
    moments = cv2.moments(resized)
    if moments["m00"] > 0:
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
    else:
        cx, cy = new_w // 2, new_h // 2
    off_x = size // 2 - cx
    off_y = size // 2 - cy
    off_x = max(0, min(size - new_w, off_x))
    off_y = max(0, min(size - new_h, off_y))
    canvas[off_y : off_y + new_h, off_x : off_x + new_w] = resized
    return canvas
