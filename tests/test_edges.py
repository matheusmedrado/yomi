from __future__ import annotations

import numpy as np

from pipeline.edges import canny, laplacian, sobel


def _gray():
    return np.random.randint(0, 256, (80, 80), dtype=np.uint8)


def test_sobel_returns_uint8_same_shape():
    out = sobel(_gray())
    assert out.shape == (80, 80)
    assert out.dtype == np.uint8


def test_laplacian_returns_uint8_same_shape():
    out = laplacian(_gray())
    assert out.shape == (80, 80)
    assert out.dtype == np.uint8


def test_canny_returns_binary_edges():
    out = canny(_gray())
    assert out.shape == (80, 80)
    assert set(np.unique(out).tolist()).issubset({0, 255})
