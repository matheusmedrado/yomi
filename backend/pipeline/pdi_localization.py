"""Propostas clássicas de regiões de texto para o modo PDI-only."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import cv2
import numpy as np

from .conditioning import _clean_mask, _ink_mask, normalize_crop
from .segmentation import TextRegion, cluster_lines, find_speech_bubbles


@dataclass
class PdiLine:
    """Linha candidata nas coordenadas originais da página."""

    x: int
    y: int
    w: int
    h: int
    vertical: bool
    raw: np.ndarray


@dataclass
class PdiRegion:
    """Região que contém uma ou mais linhas candidatas."""

    x: int
    y: int
    w: int
    h: int
    vertical: bool
    lines: list[PdiLine] = field(default_factory=list)
    source: str = "components"


def rlsa(mask: np.ndarray, horizontal_gap: int = 11,
         vertical_gap: int = 11) -> np.ndarray:
    """Aproximação de RLSA usando fechamento direcional.

    O fechamento conecta trechos de primeiro plano separados por lacunas curtas.
    """
    if mask.ndim != 2:
        raise ValueError("RLSA expects a 2D binary mask")
    horizontal_gap = max(1, int(horizontal_gap))
    vertical_gap = max(1, int(vertical_gap))
    horizontal = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_gap, 1)),
    )
    vertical = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_gap)),
    )
    return cv2.bitwise_or(horizontal, vertical)


def _union(regions: Iterable[TextRegion]) -> tuple[int, int, int, int] | None:
    regions = list(regions)
    if not regions:
        return None
    x0 = min(r.x for r in regions)
    y0 = min(r.y for r in regions)
    x1 = max(r.x + r.w for r in regions)
    y1 = max(r.y + r.h for r in regions)
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def _component_lines(mask: np.ndarray, vertical: bool) -> list[tuple[int, int, int, int]]:
    """Encontra CCs e os agrupa em linhas com RLSA e sobreposição."""
    h, w = mask.shape
    scale = max(3, int(round(min(h, w) * 0.018)))
    smoothed = rlsa(
        mask,
        horizontal_gap=max(3, min(60, scale * 3)),
        vertical_gap=max(3, min(60, scale * 3)),
    )
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(smoothed, 8)
    min_area = max(4, int(mask.size * 0.000015))
    components: list[TextRegion] = []
    for label in range(1, count):
        x, y, bw, bh, area = [int(v) for v in stats[label]]
        if area < min_area:
            continue
        if bw * bh > mask.size * 0.03:
            continue
        fill = float(area) / max(1, bw * bh)
        if fill < 0.01 or fill > 0.92:
            continue
        components.append(TextRegion(x, y, bw, bh, id=label))

    grouped = cluster_lines(components, gap_factor=0.22, vertical=vertical)
    out: list[tuple[int, int, int, int]] = []
    for group in grouped:
        box = _union(group)
        if box is None:
            continue
        x, y, bw, bh = box
        if bw * bh < max(12, mask.size * 0.00002):
            continue
        if (bw > 0.45 * w or bh > 0.45 * h):
            for component in group:
                if component.w * component.h < max(12, mask.size * 0.00002):
                    continue
                if component.w <= 0.16 * w and component.h <= 0.16 * h:
                    out.append((component.x, component.y,
                                component.w, component.h))
            continue
        out.append(box)
    return out


def _line_from_box(page: np.ndarray, box: tuple[int, int, int, int],
                   offset: tuple[int, int] = (0, 0), vertical: bool = False) -> PdiLine:
    ox, oy = offset
    x, y, w, h = box
    x += ox
    y += oy
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(page.shape[1], x + w), min(page.shape[0], y + h)
    raw = page[y0:y1, x0:x1].copy()
    if vertical and raw.size:
        raw = cv2.rotate(raw, cv2.ROTATE_90_CLOCKWISE)
    return PdiLine(x0, y0, max(1, x1 - x0), max(1, y1 - y0), vertical, raw)


def localize_roi(page: np.ndarray, roi: tuple[int, int, int, int],
                 vertical_hint: bool = False) -> PdiRegion:
    """Relocaliza linhas em uma ROI do detector usando somente PDI."""
    x, y, w, h = [int(v) for v in roi]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(page.shape[1], x + w), min(page.shape[0], y + h)
    crop = page[y0:y1, x0:x1]
    if crop.size == 0:
        return PdiRegion(x0, y0, 1, 1, vertical_hint, source="empty")
    enhanced = normalize_crop(crop)
    mask = _clean_mask(_ink_mask(enhanced))
    vertical = bool(vertical_hint or (h > w * 1.25))
    boxes = _component_lines(mask, vertical=vertical)
    lines = [_line_from_box(page, b, (x0, y0), vertical) for b in boxes]
    return PdiRegion(x0, y0, max(1, x1 - x0), max(1, y1 - y0), vertical, lines, "roi")


def _overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    return inter / max(1, min(aw * ah, bw * bh))


def localize_page(page: np.ndarray) -> list[PdiRegion]:
    """Gera regiões com limiarização, morfologia e componentes."""
    gray = normalize_crop(page)
    regions: list[PdiRegion] = []

    bubble_regions = find_speech_bubbles(gray)
    for bubble in bubble_regions:
        region = localize_roi(page, (bubble.x, bubble.y, bubble.w, bubble.h),
                              vertical_hint=bubble.h > bubble.w * 1.25)
        if region.lines:
            region.source = "bubble_pdi"
            regions.append(region)

    mask = _clean_mask(_ink_mask(gray))
    for vertical in (False, True):
        for box in _component_lines(mask, vertical=vertical):
            absolute = (box[0], box[1], box[2], box[3])
            if any(_overlap(absolute, (r.x, r.y, r.w, r.h)) > 0.35 for r in regions):
                continue
            line = _line_from_box(page, box, vertical=vertical)
            regions.append(PdiRegion(line.x, line.y, line.w, line.h, vertical,
                                     [line], "global_components"))

    regions.sort(key=lambda r: (r.y, -r.x))
    return regions
