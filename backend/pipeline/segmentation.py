from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class TextRegion:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)


def otsu_threshold(gray: np.ndarray) -> np.ndarray:
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def morphology_cleanup(
    binary: np.ndarray,
    close_ksize: int = 3,
    open_ksize: int = 3,
) -> np.ndarray:
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (close_ksize, close_ksize))
    open_k = cv2.getStructuringElement(cv2.MORPH_RECT, (open_ksize, open_ksize))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_k)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, open_k)
    return cleaned


def connected_components(
    binary: np.ndarray,
    min_area: int = 30,
    max_area: int | None = None,
    min_aspect: float = 0.05,
    max_aspect: float = 40.0,
) -> list[TextRegion]:
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8, cv2.CV_32S)
    regions: list[TextRegion] = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue
        aspect = w / float(h) if h > 0 else 0.0
        if aspect < min_aspect or aspect > max_aspect:
            continue
        regions.append(TextRegion(int(x), int(y), int(w), int(h)))
    return regions


def cluster_lines(
    regions: list[TextRegion],
    line_tol_factor: float = 0.7,
    gap_tol_factor: float = 2.0,
    min_size: int = 10,
) -> list[TextRegion]:
    if not regions:
        return []

    heights = [r.h for r in regions if r.h > 0]
    widths = [r.w for r in regions if r.w > 0]
    line_tol = int(line_tol_factor * (sorted(heights)[len(heights) // 2] if heights else 20))
    line_tol = max(line_tol, 6)
    gap_tol = int(gap_tol_factor * (sorted(widths)[len(widths) // 2] if widths else 20))
    gap_tol = max(gap_tol, 8)

    bins: dict[int, list[TextRegion]] = {}
    for region in regions:
        bin_key = int(round((region.y + region.h / 2.0) / line_tol))
        bins.setdefault(bin_key, []).append(region)

    lines: list[TextRegion] = []
    for bin_regions in bins.values():
        for region in sorted(bin_regions, key=lambda r: r.x):
            placed = False
            for run in lines:
                if abs((run.y + run.h / 2) - (region.y + region.h / 2)) > line_tol:
                    continue
                if region.x <= run.x + run.w + gap_tol:
                    run.x = min(run.x, region.x)
                    run.y = min(run.y, region.y)
                    run.w = max(run.x + run.w, region.x + region.w) - run.x
                    run.h = max(run.y + run.h, region.y + region.h) - run.y
                    placed = True
                    break
            if not placed:
                lines.append(TextRegion(region.x, region.y, region.w, region.h))

    return sorted(
        (r for r in lines if r.w >= min_size and r.h >= min_size),
        key=lambda r: (r.y, r.x),
    )



def watershed(binary: np.ndarray, src: np.ndarray | None = None) -> np.ndarray:
    if src is None:
        src = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.5 * dist.max(), 255, 0)
    sure_fg = sure_fg.astype(np.uint8)
    _, sure_bg = cv2.connectedComponents(sure_fg)
    unknown = cv2.subtract(cv2.dilate(binary, np.ones((3, 3), np.uint8), 1), sure_fg)
    markers = sure_bg + 1
    markers[unknown == 255] = 0
    if src.ndim == 2:
        src = cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
    return cv2.watershed(src, markers)


def detect_text_regions(
    gray: np.ndarray,
    min_area: int = 60,
    max_area: int = 8000,
    cluster: bool = True,
) -> list[TextRegion]:
    binary = otsu_threshold(gray)
    binary = morphology_cleanup(binary)
    regions = connected_components(binary, min_area=min_area, max_area=max_area)
    if cluster:
        regions = cluster_lines(regions)
    return regions
