from __future__ import annotations

import numpy as np

from pipeline.ocr import features


def test_zoning_vector_length_and_range():
    glyph = np.zeros((64, 64), dtype=np.uint8)
    glyph[16:48, 16:48] = 255
    vec = features.zoning_vector(glyph, grid=8)
    assert vec.shape == (64,)
    assert vec.min() >= 0.0 and vec.max() <= 1.0
    assert vec.sum() > 0


def test_correlation_identical_is_one():
    glyph = np.zeros((32, 32), dtype=np.uint8)
    glyph[8:24, 8:24] = 255
    assert abs(features.correlation_score(glyph, glyph) - 1.0) < 1e-6


def test_correlation_disimilar_is_lower():
    a = np.zeros((32, 32), dtype=np.uint8)
    a[8:24, 8:24] = 255
    b = np.zeros((32, 32), dtype=np.uint8)
    b[0:16, 0:16] = 255
    assert features.correlation_score(a, b) < features.correlation_score(a, a)
