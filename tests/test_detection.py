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


def test_baseline_mode_keeps_raw_crops_without_conditioning():
    class FakeLineBlock:
        xyxy = (0, 0, 80, 70)
        vertical = False
        font_size = 12

        def lines_array(self):
            return [object()]

        def get_transformed_region(self, image, _line_index, _height):
            return image[:64, :80]

    class FakeDetector:
        available = True

        def detect(self, image):
            return np.zeros(image.shape[:2], np.uint8), np.zeros(image.shape[:2], np.uint8), [FakeLineBlock()]

    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    blocks = detect_blocks(image, detector=FakeDetector(), mode="baseline")
    assert blocks and blocks[0].crops and not blocks[0].conditioning


def test_median_restore_mode_filters_crop_before_ocr():
    class FakeLineBlock:
        xyxy = (0, 0, 80, 70)
        vertical = False
        font_size = 12

        def lines_array(self):
            return [object()]

        def get_transformed_region(self, image, _line_index, _height):
            return image[:64, :80]

    class FakeDetector:
        available = True

        def detect(self, image):
            empty = np.zeros(image.shape[:2], np.uint8)
            return empty, empty, [FakeLineBlock()]

    image = np.full((100, 100, 3), 127, dtype=np.uint8)
    image[20, 20] = 255
    expected = cv2.cvtColor(
        cv2.medianBlur(cv2.cvtColor(image[:64, :80], cv2.COLOR_BGR2GRAY), 3),
        cv2.COLOR_GRAY2BGR,
    )

    blocks = detect_blocks(image, detector=FakeDetector(), mode="median_restore")

    assert blocks and len(blocks[0].crops) == 1
    assert np.array_equal(blocks[0].crops[0], expected)
    assert np.array_equal(blocks[0].original_crops[0], image[:64, :80])
    assert not blocks[0].conditioning


def test_pdi_only_mode_does_not_call_detector(monkeypatch):
    image = np.full((120, 240, 3), 255, dtype=np.uint8)
    cv2.putText(image, "PDI", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.4,
                (0, 0, 0), 2, cv2.LINE_AA)

    def fail(*_args, **_kwargs):
        raise AssertionError("detector should not be called in pdi_only mode")

    monkeypatch.setattr("pipeline.detection.get_detector", fail)
    blocks = detect_blocks(image, mode="pdi_only")
    assert isinstance(blocks, list)
