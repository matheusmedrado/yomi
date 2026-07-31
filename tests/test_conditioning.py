"""Unit tests for the mandatory classical OCR conditioning stage."""
from __future__ import annotations

import logging

import cv2
import numpy as np
import pytest

from pipeline.conditioning import condition_crop
from pipeline import detection


def _text_crop(*, inverted: bool = False, width: int = 320) -> np.ndarray:
    paper, ink = (0, 255) if inverted else (255, 0)
    crop = np.full((72, width, 3), paper, dtype=np.uint8)
    cv2.putText(crop, "TEXT", (16, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.35,
                (ink, ink, ink), 2, cv2.LINE_AA)
    return crop


@pytest.mark.parametrize("inverted", [False, True])
def test_valid_horizontal_and_inverted_ink_produce_conditioned_crops(inverted):
    result = condition_crop(_text_crop(inverted=inverted))
    assert result.valid_mask
    assert result.fallback is None
    assert result.crops and all(c.size for c in result.crops)
    assert not result.used_raw


def test_noisy_background_still_produces_a_tight_processed_crop():
    rng = np.random.default_rng(3)
    crop = _text_crop()
    noise = rng.normal(0, 9, crop.shape).astype(np.int16)
    noisy = np.clip(crop.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    result = condition_crop(noisy)
    assert result.valid_mask
    assert result.fallback is None
    assert result.crops[0].shape[1] < noisy.shape[1]


def test_vertical_text_is_conditioned_after_horizontalization():
    # Detection rotates vertical columns first; a rotated synthetic column is
    # therefore an ordinary horizontalized conditioning input here.
    vertical = np.full((320, 72, 3), 255, dtype=np.uint8)
    cv2.putText(vertical, "I", (24, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                (0, 0, 0), 2)
    horizontalized = cv2.rotate(vertical, cv2.ROTATE_90_CLOCKWISE)
    result = condition_crop(horizontalized)
    assert result.crops and result.fallback is None


def test_long_line_splits_at_classical_projection_gaps():
    crop = np.full((72, 1100, 3), 255, dtype=np.uint8)
    for x in (20, 230, 440, 650, 860):
        cv2.putText(crop, "AB", (x, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.25,
                    (0, 0, 0), 2, cv2.LINE_AA)
    result = condition_crop(crop, max_ratio=4)
    assert result.valid_mask
    assert len(result.crops) > 1
    assert result.cut_points


def test_empty_crop_uses_processed_normalized_fallback_not_raw():
    blank = np.full((72, 240, 3), 255, dtype=np.uint8)
    result = condition_crop(blank)
    assert result.fallback == "normalized"
    assert not result.used_raw
    assert result.crops[0].ndim == 3
    # The first fallback is still CLAHE/bilateral grayscale represented in BGR.
    assert np.array_equal(result.crops[0][:, :, 0], result.crops[0][:, :, 1])


def test_truly_empty_crop_is_rejected_for_the_detection_adapter_to_recover():
    with pytest.raises(ValueError, match="empty detector crop"):
        condition_crop(np.empty((0, 0, 3), dtype=np.uint8))


class _FakeBlock:
    xyxy = (5, 6, 80, 70)
    vertical = False
    font_size = 12

    def lines_array(self):
        return [object()]

    def get_transformed_region(self, _img, _line_index, _height):
        return _text_crop()


class _FakeDetector:
    available = True

    def detect(self, _img):
        return np.zeros((10, 10), np.uint8), np.zeros((10, 10), np.uint8), [_FakeBlock()]


def test_raw_fallback_is_logged_only_when_conditioning_throws(monkeypatch, caplog):
    def explode(_crop, max_ratio):
        raise RuntimeError("injected conditioning failure")

    monkeypatch.setattr(detection, "condition_crop", explode)
    with caplog.at_level(logging.WARNING, logger="pipeline.detection"):
        blocks = detection.detect_blocks(np.full((100, 100, 3), 255, np.uint8),
                                         detector=_FakeDetector(), mode="hybrid")
    result = blocks[0].conditioning[0]
    assert result.used_raw
    assert np.array_equal(result.crops[0], result.raw)
    assert "raw_fallback" in caplog.text
