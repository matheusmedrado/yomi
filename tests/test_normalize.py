from __future__ import annotations

import numpy as np

from pipeline.ocr.normalize import crop_to_bbox, normalize_glyph, to_binary


def test_to_binary_inverts_grayscale_ink():
    img = np.full((20, 20), 255, dtype=np.uint8)
    cv2 = __import__("cv2")
    cv2.rectangle(img, (5, 5), (10, 10), 0, -1)
    binary = to_binary(img)
    assert binary[7, 7] == 255
    assert binary[0, 0] == 0


def test_to_binary_passthrough_on_binary():
    binary = np.zeros((10, 10), dtype=np.uint8)
    binary[2:4, 2:4] = 255
    assert np.array_equal(to_binary(binary), binary)


def test_crop_to_bbox_returns_none_for_empty():
    assert crop_to_bbox(np.zeros((10, 10), dtype=np.uint8)) is None


def test_normalize_glyph_shape_and_ink():
    img = np.full((40, 40), 255, dtype=np.uint8)
    cv2 = __import__("cv2")
    cv2.rectangle(img, (10, 10), (30, 30), 0, -1)
    normalized = normalize_glyph(img, size=64)
    assert normalized.shape == (64, 64)
    assert normalized.max() == 255
    assert normalized.sum() > 0


def test_normalize_glyph_blank_for_empty():
    assert normalize_glyph(np.zeros((20, 20), dtype=np.uint8)).sum() == 0
