from __future__ import annotations

import cv2
import numpy as np

from pipeline.pdi_localization import localize_page, localize_roi, rlsa


def test_rlsa_connects_runs_without_changing_shape():
    mask = np.zeros((40, 120), dtype=np.uint8)
    mask[18:22, 10:20] = 255
    mask[18:22, 26:36] = 255
    joined = rlsa(mask, horizontal_gap=10, vertical_gap=3)
    assert joined.shape == mask.shape
    assert np.count_nonzero(joined[:, 20:26]) > 0


def test_pdi_roi_localization_returns_classical_lines():
    image = np.full((120, 300, 3), 255, dtype=np.uint8)
    cv2.putText(image, "AB", (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(image, "CD", (20, 98), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 0, 0), 2, cv2.LINE_AA)
    region = localize_roi(image, (0, 0, 300, 120))
    assert region.source == "roi"
    assert region.lines
    assert all(line.raw.size for line in region.lines)


def test_pdi_page_localization_does_not_require_detector():
    image = np.full((180, 360, 3), 255, dtype=np.uint8)
    cv2.putText(image, "PDI", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                (0, 0, 0), 3, cv2.LINE_AA)
    regions = localize_page(image)
    assert isinstance(regions, list)
    assert all(r.lines for r in regions)
