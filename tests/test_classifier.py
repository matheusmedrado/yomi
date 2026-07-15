from __future__ import annotations

import numpy as np
import pytest

from pipeline.ocr.classifier import TemplateClassifier
from tests.conftest import render_text


def test_classify_self_template_is_exact(template_db):
    clf = TemplateClassifier(template_db)
    for idx in range(0, len(template_db.images), 37):
        char, conf = clf.classify(template_db.images[idx], k=3)
        assert char == template_db.labels[idx]
        assert conf > 0.9


def test_ocr_region_returns_expected_keys(template_db, font):
    clf = TemplateClassifier(template_db)
    gray = render_text("カタカナ", font)
    result = clf.ocr_region(gray, k=3)
    assert "text" in result and "glyphs" in result
    assert result["text"] == "カタカナ"
    assert result["count"] == len(result["glyphs"])


def test_ocr_region_blank_returns_empty(template_db):
    clf = TemplateClassifier(template_db)
    gray = np.full((60, 200), 255, dtype=np.uint8)
    result = clf.ocr_region(gray, k=3)
    assert result["text"] == ""
    assert result["count"] == 0
