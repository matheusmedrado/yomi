from __future__ import annotations

import numpy as np

from pipeline.preprocess import (
    clahe_equalize,
    color_to_text_mask,
    denoise,
    preprocess_page,
    resize_longest_edge,
    to_grayscale,
)


def test_to_grayscale_shape():
    color = np.zeros((30, 40, 3), dtype=np.uint8)
    gray = to_grayscale(color)
    assert gray.shape == (30, 40)
    assert gray.ndim == 2


def test_grayscale_idempotent():
    gray = np.zeros((20, 20), dtype=np.uint8)
    assert to_grayscale(gray) is not None


def test_resize_longest_edge_scales_down():
    img = np.zeros((800, 400), dtype=np.uint8)
    out = resize_longest_edge(img, 200)
    assert max(out.shape) == 200


def test_resize_longest_edge_no_upscale_when_small():
    img = np.zeros((50, 50), dtype=np.uint8)
    out = resize_longest_edge(img, 200)
    assert out.shape == (50, 50)


def test_clahe_preserves_shape_and_range():
    gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    out = clahe_equalize(gray)
    assert out.shape == gray.shape
    assert out.min() >= 0 and out.max() <= 255


def test_denoise_returns_same_shape():
    gray = np.random.randint(0, 256, (60, 60), dtype=np.uint8)
    for method in ("gaussian", "median", "bilateral"):
        out = denoise(gray, method=method)
        assert out.shape == gray.shape


def test_color_to_text_mask_shape_and_binary():
    img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    mask = color_to_text_mask(img)
    assert mask.shape == (50, 50)
    assert set(np.unique(mask).tolist()).issubset({0, 255})


def test_preprocess_page_returns_gray_and_mask():
    color = np.random.randint(0, 256, (300, 200, 3), dtype=np.uint8)
    gray, mask = preprocess_page(color, target_longest=160)
    assert gray.shape[0] == 160
    assert gray.shape[1] == 107
    assert mask.shape == (300, 200)
    assert gray.dtype == np.uint8

