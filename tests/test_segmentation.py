from __future__ import annotations

import cv2
import numpy as np

from pipeline.segmentation import (
    TextRegion,
    cluster_lines,
    connected_components,
    detect_text_regions,
    morphology_cleanup,
    otsu_threshold,
)


def _with_rectangles() -> np.ndarray:
    img = np.full((200, 300), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 60), 0, -1)
    cv2.rectangle(img, (150, 100), (210, 150), 0, -1)
    return img


def test_otsu_separates_ink():
    binary = otsu_threshold(_with_rectangles())
    assert binary.shape == (200, 300)
    assert binary.max() == 255


def test_connected_components_finds_two_rectangles():
    binary = morphology_cleanup(otsu_threshold(_with_rectangles()))
    regions = connected_components(binary, min_area=10)
    assert len(regions) == 2


def test_clustering_merges_into_lines():
    regions = [
        TextRegion(10, 10, 20, 20),
        TextRegion(40, 12, 20, 20),
        TextRegion(10, 100, 20, 20),
    ]
    lines = cluster_lines(regions)
    assert len(lines) == 2


def test_detect_text_regions_on_synthetic():
    regs = detect_text_regions(_with_rectangles(), min_area=10)
    assert len(regs) == 2
