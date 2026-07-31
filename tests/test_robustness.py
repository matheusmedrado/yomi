from __future__ import annotations

import cv2
import numpy as np

from pipeline.robustness import (
    DEGRADATIONS,
    add_gaussian_noise,
    add_salt_pepper,
    degradation_triplet,
    reduce_contrast,
    restore,
)


def _text_crop() -> np.ndarray:
    image = np.full((80, 320, 3), 245, dtype=np.uint8)
    cv2.putText(image, "PDI", (20, 58), cv2.FONT_HERSHEY_SIMPLEX,
                1.7, (15, 15, 15), 3, cv2.LINE_AA)
    return image


def test_degradations_are_deterministic_and_preserve_shape():
    image = _text_crop()
    for kind in DEGRADATIONS:
        original, degraded_a, restored = degradation_triplet(image, kind, seed=7)
        _, degraded_b, _ = degradation_triplet(image, kind, seed=7)
        assert original.shape == degraded_a.shape == restored.shape
        assert original.dtype == degraded_a.dtype == restored.dtype == np.uint8
        assert np.array_equal(degraded_a, degraded_b)


def test_low_contrast_compresses_range_and_equalization_expands_it():
    image = _text_crop()
    degraded = reduce_contrast(image)
    restored = restore(degraded, "low_contrast")
    assert np.ptp(degraded[:, :, 0]) < np.ptp(image[:, :, 0])
    assert np.ptp(restored[:, :, 0]) > np.ptp(degraded[:, :, 0])


def test_gaussian_filter_reduces_gaussian_noise_error():
    image = _text_crop()
    noisy = add_gaussian_noise(image, sigma=38, seed=2)
    restored = restore(noisy, "gaussian_noise")
    clean = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    noisy_error = np.mean((noisy[:, :, 0].astype(np.float32) - clean) ** 2)
    restored_error = np.mean((restored[:, :, 0].astype(np.float32) - clean) ** 2)
    assert restored_error < noisy_error


def test_median_reduces_salt_and_pepper_error():
    image = _text_crop()
    noisy = add_salt_pepper(image, density=0.10, seed=2)
    restored = restore(noisy, "salt_pepper")
    clean = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    noisy_error = np.mean((noisy[:, :, 0].astype(np.float32) - clean) ** 2)
    restored_error = np.mean((restored[:, :, 0].astype(np.float32) - clean) ** 2)
    assert restored_error < noisy_error
