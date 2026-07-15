from __future__ import annotations

import cv2
import numpy as np


def zoning_vector(binary: np.ndarray, grid: int = 8) -> np.ndarray:
    h, w = binary.shape
    cell_h = h / grid
    cell_w = w / grid
    vec = np.zeros(grid * grid, dtype=np.float32)
    for r in range(grid):
        for c in range(grid):
            y0, y1 = int(r * cell_h), int((r + 1) * cell_h)
            x0, x1 = int(c * cell_w), int((c + 1) * cell_w)
            block = binary[y0:y1, x0:x1]
            total = max(1, block.size)
            vec[r * grid + c] = float(np.count_nonzero(block)) / total
    return vec


def correlation_score(template: np.ndarray, query: np.ndarray) -> float:
    if template.shape != query.shape:
        return 0.0
    result = cv2.matchTemplate(query, template, cv2.TM_CCORR_NORMED)
    return float(result[0, 0])
