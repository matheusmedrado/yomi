"""Tests for the DL text detector + classical post-processing split."""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.detection import (  # noqa: E402
    _HAS_DETECTOR,
    get_detector,
    detect_blocks,
)

SAMPLE = Path(__file__).resolve().parent.parent / "backend" / "data" / "samples" / "sample.png"


@pytest.mark.skipif(not (_HAS_DETECTOR and SAMPLE.is_file()),
                    reason="comic-text-detector model or sample page missing")
def test_detect_blocks_finds_bubbles():
    img = cv2.imread(str(SAMPLE))
    detector = get_detector(device="cpu")
    assert detector.available, "comictextdetector.pt not found"

    blocks = detect_blocks(img, detector=detector)
    # The sample page has 7 speech bubbles with text.
    assert len(blocks) >= 5

    # Each block carries an OCR-ready crop.
    total_crops = sum(len(b.crops) for b in blocks)
    assert total_crops >= len(blocks)

    # Vertical text should dominate (manga).
    vertical = [b for b in blocks if b.vertical]
    assert len(vertical) >= 1


@pytest.mark.skipif(not (_HAS_DETECTOR and SAMPLE.is_file()),
                    reason="comic-text-detector model or sample page missing")
def test_block_crops_are_nonempty():
    img = cv2.imread(str(SAMPLE))
    blocks = detect_blocks(img, detector=get_detector(device="cpu"))
    for b in blocks:
        for crop in b.crops:
            assert crop is not None and crop.size > 0
            assert crop.ndim == 3 and crop.shape[2] == 3
