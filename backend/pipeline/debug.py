"""Pipeline debug visualizations.

Used by the `/api/debug/<stage>/<session_id>/<n>` endpoint to return
intermediate images of the classical PDI pipeline (gray, mask, Otsu, CC,
watershed). This is what we point the professor at during the demo to
show that the work isn't magic — each stage is a real lab technique.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import preprocess, segmentation


def _load_image(path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img


def stage_gray(path, target: int = 1200) -> np.ndarray:
    img = _load_image(path)
    gray, _ = preprocess.preprocess_page(img, target_longest=target)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def stage_mask(path) -> np.ndarray:
    img = _load_image(path)
    mask = preprocess.color_to_text_mask(img)
    return cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)


def stage_otsu(path, target: int = 1200) -> np.ndarray:
    img = _load_image(path)
    gray, mask = preprocess.preprocess_page(img, target_longest=target)
    if mask.shape[:2] != gray.shape[:2]:
        mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    binary = segmentation.otsu_threshold(mask)
    binary = segmentation.morphology_cleanup(binary)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def stage_cc(path, target: int = 1200) -> np.ndarray:
    img = _load_image(path)
    gray, mask = preprocess.preprocess_page(img, target_longest=target)
    if mask.shape[:2] != gray.shape[:2]:
        mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    binary = segmentation.otsu_threshold(mask)
    binary = segmentation.morphology_cleanup(binary)
    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    regions = segmentation.connected_components(binary, min_area=80)
    for r in regions:
        cv2.rectangle(color, (r.x, r.y), (r.x + r.w, r.y + r.h),
                      (200, 16, 46), 2)
    return color


def stage_watershed(path, target: int = 1200) -> np.ndarray:
    img = _load_image(path)
    gray, mask = preprocess.preprocess_page(img, target_longest=target)
    if mask.shape[:2] != gray.shape[:2]:
        mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    binary = segmentation.otsu_threshold(mask)
    binary = segmentation.morphology_cleanup(binary)
    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    components = segmentation.connected_components(binary, min_area=80)
    for c in components:
        for r in segmentation.watershed_split(binary, c):
            cv2.rectangle(color, (r.x, r.y), (r.x + r.w, r.y + r.h),
                          (10, 10, 10), 2)
    return color


STAGES = {
    "gray": stage_gray,
    "mask": stage_mask,
    "otsu": stage_otsu,
    "cc": stage_cc,
    "watershed": stage_watershed,
}
