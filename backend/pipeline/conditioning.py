"""Condicionamento PDI dos recortes enviados ao OCR."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import cv2
import numpy as np

from .preprocess import clahe_equalize, denoise, to_grayscale


DEFAULT_MAX_RATIO = 8.0


@dataclass
class ConditioningResult:
    """Resultado inspecionável do condicionamento de um recorte horizontal."""

    crops: List[np.ndarray]
    raw: np.ndarray
    enhanced: np.ndarray
    mask: np.ndarray
    components_overlay: np.ndarray
    projection: np.ndarray
    cut_points: List[int] = field(default_factory=list)
    fallback: str | None = None
    valid_mask: bool = True

    @property
    def used_raw(self) -> bool:
        return self.fallback == "raw_fallback"


def _as_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def normalize_crop(crop_bgr: np.ndarray) -> np.ndarray:
    """Aplica tons de cinza, CLAHE e filtro bilateral."""
    if crop_bgr is None or crop_bgr.size == 0:
        raise ValueError("empty detector crop")
    gray = to_grayscale(crop_bgr)
    enhanced = clahe_equalize(gray, clip_limit=2.0, tile_grid=(8, 8))
    enhanced = denoise(enhanced, method="bilateral", ksize=3)
    return enhanced


def _ink_mask(enhanced: np.ndarray) -> np.ndarray:
    """Limiar de Otsu com polaridade automática para tinta clara ou escura.

    Escolhe como tinta a classe mais esparsa produzida por Otsu.
    """
    _, dark_ink = cv2.threshold(
        enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    _, light_ink = cv2.threshold(
        enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    dark_fraction = np.count_nonzero(dark_ink) / dark_ink.size
    light_fraction = np.count_nonzero(light_ink) / light_ink.size

    def score(fraction: float) -> float:
        return abs(fraction - 0.12) + (0.8 if fraction < 0.002 or fraction > 0.65 else 0)

    return dark_ink if score(dark_fraction) <= score(light_fraction) else light_ink


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    """A abertura remove pixels isolados e o fechamento une pequenas falhas."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    out = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(out, cv2.MORPH_CLOSE, kernel)


def _component_geometry(mask: np.ndarray) -> tuple[bool, tuple[int, int, int, int] | None, np.ndarray]:
    """Valida a cobertura de tinta e obtém uma caixa unida pelos CCs."""
    h, w = mask.shape
    coverage = float(np.count_nonzero(mask)) / max(1, mask.size)
    overlay = _as_bgr(mask)
    if not 0.002 <= coverage <= 0.60:
        return False, None, overlay

    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    minimum_area = max(2, int(round(mask.size * 0.00003)))
    boxes: list[tuple[int, int, int, int]] = []
    kept_area = 0
    for label in range(1, count):
        x, y, bw, bh, area = [int(v) for v in stats[label]]
        if area < minimum_area:
            continue
        boxes.append((x, y, bw, bh))
        kept_area += area
        cv2.rectangle(overlay, (x, y), (x + bw - 1, y + bh - 1), (0, 180, 0), 1)
    if not boxes or kept_area / max(1, mask.size) < 0.0015:
        return False, None, overlay

    x0 = min(x for x, _y, _w, _h in boxes)
    y0 = min(y for _x, y, _w, _h in boxes)
    x1 = max(x + bw for x, _y, bw, _h in boxes)
    y1 = max(y + bh for _x, y, _w, bh in boxes)
    pad = max(2, int(round(min(h, w) * 0.04)))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return False, None, overlay
    cv2.rectangle(overlay, (x0, y0), (x1 - 1, y1 - 1), (0, 0, 255), 1)
    return True, (x0, y0, x1, y1), overlay


def _smooth_profile(mask: np.ndarray) -> np.ndarray:
    density = mask.astype(np.float32).sum(axis=0) / 255.0
    sigma = max(1.0, mask.shape[0] / 10.0)
    requested = max(3, int(round(sigma * 6)) | 1)
    max_width = density.size if density.size % 2 else density.size - 1
    kernel_width = max(1, min(requested, max_width))
    kernel = cv2.getGaussianKernel(kernel_width, sigma).reshape(-1)
    return np.convolve(density, kernel, mode="same")


def _split_at_low_ink_gaps(image: np.ndarray, mask: np.ndarray,
                           max_ratio: float) -> tuple[List[np.ndarray], List[int], np.ndarray]:
    """Divide recortes horizontais longos nos mínimos de tinta suavizados."""
    h, w = image.shape[:2]
    profile = _smooth_profile(mask)
    cuts: list[int] = []
    if h > 0 and w / h > max_ratio:
        parts = int(np.ceil((w / h) / max_ratio))
        half_window = max(3, int(round(h * 1.5)))
        for anchor in np.linspace(0, w, parts + 1)[1:-1]:
            lo = max(1, int(anchor - half_window))
            hi = min(w - 1, int(anchor + half_window))
            if hi <= lo:
                continue
            cut = lo + int(np.argmin(profile[lo:hi]))
            if not cuts or cut - cuts[-1] >= max(4, h // 3):
                cuts.append(cut)
        if cuts and w - cuts[-1] < max(4, h // 3):
            cuts.pop()

    chart_h = max(80, h)
    chart = np.full((chart_h, w, 3), 255, dtype=np.uint8)
    if profile.size and profile.max() > 0:
        scaled = profile / profile.max() * (chart_h - 12)
        pts = np.column_stack((np.arange(w), chart_h - 6 - scaled.astype(np.int32)))
        cv2.polylines(chart, [pts.reshape(-1, 1, 2)], False, (30, 30, 30), 1)
    for cut in cuts:
        cv2.line(chart, (cut, 0), (cut, chart_h - 1), (0, 0, 255), 1)
    return list(np.split(image, cuts, axis=1)) if cuts else [image], cuts, chart


def condition_crop(crop_bgr: np.ndarray, max_ratio: float = DEFAULT_MAX_RATIO) -> ConditioningResult:
    """Condiciona o recorte de uma linha fornecido pelo detector.

    Máscaras fracas retornam o recorte normalizado.
    """
    enhanced = normalize_crop(crop_bgr)
    mask = _clean_mask(_ink_mask(enhanced))
    valid, bounds, overlay = _component_geometry(mask)
    if not valid or bounds is None:
        full_mask = mask
        crops, cuts, projection = _split_at_low_ink_gaps(_as_bgr(enhanced), full_mask, max_ratio)
        return ConditioningResult(
            crops=crops, raw=crop_bgr, enhanced=enhanced, mask=mask,
            components_overlay=overlay, projection=projection,
            cut_points=cuts, fallback="normalized", valid_mask=False,
        )

    x0, y0, x1, y1 = bounds
    enhanced_crop = enhanced[y0:y1, x0:x1]
    mask_crop = mask[y0:y1, x0:x1]
    crops, cuts, projection = _split_at_low_ink_gaps(
        _as_bgr(enhanced_crop), mask_crop, max_ratio
    )
    return ConditioningResult(
        crops=crops, raw=crop_bgr, enhanced=enhanced, mask=mask,
        components_overlay=overlay, projection=projection, cut_points=cuts,
    )


def raw_fallback(crop_bgr: np.ndarray, reason: str = "raw_fallback") -> ConditioningResult:
    """Monta dados de depuração para a única recuperação com pixels crus."""
    if crop_bgr is None or crop_bgr.size == 0:
        raise ValueError("empty detector crop")
    gray = to_grayscale(crop_bgr)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    return ConditioningResult(
        crops=[crop_bgr], raw=crop_bgr, enhanced=gray, mask=mask,
        components_overlay=_as_bgr(mask),
        projection=np.full((max(80, gray.shape[0]), gray.shape[1], 3), 255, dtype=np.uint8),
        fallback=reason, valid_mask=False,
    )
