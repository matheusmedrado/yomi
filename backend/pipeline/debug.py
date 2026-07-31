"""Visualizações de depuração do pipeline."""
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

CONDITIONING_STAGES = {
    "conditioning_raw",
    "conditioning_enhanced",
    "conditioning_mask",
    "conditioning_components",
    "conditioning_projection",
    "conditioning_final",
    "conditioning_overlay",
}


def _selected_conditioning(blocks):
    for block in blocks:
        if getattr(block, "conditioning", None):
            return block, block.conditioning[0]
    return None, None


def _status_board(message: str) -> np.ndarray:
    out = np.full((80, 420, 3), 255, dtype=np.uint8)
    cv2.putText(out, message, (12, 46), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (40, 40, 40), 1, cv2.LINE_AA)
    return out


def _crop_board(crops: list[np.ndarray]) -> np.ndarray:
    """Reúne os recortes finais do OCR em um painel legível."""
    if not crops:
        return np.full((80, 240, 3), 255, dtype=np.uint8)
    height = max(1, max(c.shape[0] for c in crops))
    tiles = []
    for crop in crops:
        if crop.ndim == 2:
            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        if crop.shape[0] != height:
            crop = cv2.resize(crop, (max(1, int(crop.shape[1] * height / crop.shape[0])), height))
        tiles.append(crop)
    gap = np.full((height, 8, 3), 230, dtype=np.uint8)
    return np.concatenate([tile for pair in zip(tiles, [gap] * len(tiles)) for tile in pair][:-1], axis=1)


def conditioning_stage(stage: str, page_bgr: np.ndarray, blocks) -> np.ndarray:
    """Renderiza evidências dos recortes ou a sobreposição da página."""
    if stage not in CONDITIONING_STAGES:
        raise ValueError(f"unknown conditioning stage: {stage}")
    if stage == "conditioning_overlay":
        out = page_bgr.copy()
        for block in blocks:
            results = getattr(block, "conditioning", [])
            states = {r.fallback for r in results}
            if not results:
                color, label = (100, 100, 100), "raw"
            elif "raw_fallback" in states:
                color, label = (30, 30, 220), "raw"
            elif "normalized" in states:
                color, label = (0, 180, 230), "normalized"
            else:
                color, label = (40, 170, 40), "pdi"
            cv2.rectangle(out, (block.x, block.y),
                          (block.x + block.w, block.y + block.h), color, 2)
            cv2.putText(out, f"{block.id}:{label}", (block.x, max(14, block.y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
        return out

    block, result = _selected_conditioning(blocks)
    if result is None:
        if block is None:
            block = next((b for b in blocks if getattr(b, "crops", None)), None)
        if stage in {"conditioning_raw", "conditioning_final"} and block is not None:
            return _crop_board(block.crops)
        return _status_board("Baseline: esta etapa não é aplicada")
    if stage == "conditioning_raw":
        return result.raw
    if stage == "conditioning_enhanced":
        return cv2.cvtColor(result.enhanced, cv2.COLOR_GRAY2BGR)
    if stage == "conditioning_mask":
        return cv2.cvtColor(result.mask, cv2.COLOR_GRAY2BGR)
    if stage == "conditioning_components":
        return result.components_overlay
    if stage == "conditioning_projection":
        return result.projection
    return _crop_board(result.crops)
