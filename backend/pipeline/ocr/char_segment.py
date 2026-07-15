from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from pipeline.ocr.normalize import normalize_glyph, to_binary


@dataclass
class Glyph:
    x: int
    y: int
    w: int
    h: int
    image: np.ndarray
    y_line: int = 0


def segment_glyphs(
    gray: np.ndarray,
    size: int = 64,
    min_area: int = 20,
    merge_gap: int = 8,
    line_tol_factor: float = 0.4,
) -> list[Glyph]:
    binary = to_binary(gray)
    h, w = binary.shape
    if h == 0 or w == 0:
        return []

    num, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8, cv2.CV_32S)
    comps: list[tuple[int, int, int, int]] = []
    for i in range(1, num):
        x, y, cw, ch, area = stats[i]
        if area < min_area:
            continue
        comps.append((x, y, cw, ch))

    if not comps:
        return []

    comps.sort(key=lambda c: c[0])
    heights = sorted(c[3] for c in comps)
    y_tol = max(6, int(line_tol_factor * heights[len(heights) // 2]))

    groups: list[list[tuple[int, int, int, int]]] = []
    current: list[tuple[int, int, int, int]] = []
    gx0 = gy0 = gx1 = gy1 = 0

    def flush() -> None:
        nonlocal current, groups
        if current:
            groups.append(current)
            current = []

    for x, y, cw, ch in comps:
        if not current:
            current = [(x, y, cw, ch)]
            gx0, gy0, gx1, gy1 = x, y, x + cw, y + ch
            continue
        gap = x - gx1
        y_overlap = not (y + ch < gy0 - y_tol or y > gy1 + y_tol)
        x_overlap = not (x > gx1 or gx0 > x + cw)
        combined_w = max(gx1, x + cw) - min(gx0, x)
        cell_limit = 1.2 * max(gy1 - gy0, ch)
        if gap <= merge_gap and y_overlap and (x_overlap or combined_w <= cell_limit):
            current.append((x, y, cw, ch))
            gx0 = min(gx0, x)
            gy0 = min(gy0, y)
            gx1 = max(gx1, x + cw)
            gy1 = max(gy1, y + ch)
        else:
            flush()
            current = [(x, y, cw, ch)]
            gx0, gy0, gx1, gy1 = x, y, x + cw, y + ch
    flush()

    glyphs: list[Glyph] = []
    for group in groups:
        gx = min(c[0] for c in group)
        gy = min(c[1] for c in group)
        gx2 = max(c[0] + c[2] for c in group)
        gy2 = max(c[1] + c[3] for c in group)
        crop = binary[gy:gy2, gx:gx2]
        glyphs.append(Glyph(gx, gy, gx2 - gx, gy2 - gy, normalize_glyph(crop, size)))

    heights = sorted(g.h for g in glyphs)
    band = max(10, int(0.6 * heights[len(heights) // 2]))
    for g in glyphs:
        g.y_line = int(round((g.y + g.h / 2.0) / band))
    glyphs.sort(key=lambda g: (g.y_line, g.x))
    return glyphs
