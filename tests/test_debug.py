"""Testes das evidências visuais usadas na demonstração do site."""
from __future__ import annotations

import cv2
import numpy as np

from pipeline.debug import RESTORATION_STAGES, STAGES, restoration_stage
from pipeline.detection import DetectedBlock


def test_debug_exposes_course_pipeline_in_order():
    assert list(STAGES) == [
        "gray", "mask", "otsu", "morphology", "cc", "watershed",
    ]


def test_restoration_comparison_contains_original_and_median_rows():
    original = np.full((64, 180, 3), 255, dtype=np.uint8)
    cv2.putText(original, "PDI", (10, 45), cv2.FONT_HERSHEY_SIMPLEX,
                1.1, (0, 0, 0), 2, cv2.LINE_AA)
    noisy = original.copy()
    noisy[10, 10] = 0
    filtered = cv2.medianBlur(noisy, 3)
    block = DetectedBlock(
        id=0, x=0, y=0, w=180, h=64, vertical=False, font_size=12,
        crops=[filtered], original_crops=[noisy],
    )

    result = restoration_stage("restoration_comparison", [block])

    assert "restoration_comparison" in RESTORATION_STAGES
    assert result.ndim == 3 and result.shape[2] == 3
    assert result.shape[0] > noisy.shape[0] * 2
    assert result.shape[1] >= noisy.shape[1]
