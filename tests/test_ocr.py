"""Skip-safe smoke tests for the manga-ocr wrapper.

These exercise the wrapper contract without forcing the heavy DL
dependency. They will:
  - run the simple call paths (no model) and assert the empty-string
    fallback works;
  - load the real model and run a single inference, but only if the
    model is already cached locally — otherwise skip.

The idea is that CI / unit tests do not need to download ~440 MB of
weights, but a developer who has the model warm can run a real check.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# conftest.py adds `backend/` to sys.path so that sibling modules
# (e.g. `language`) can be imported as top-level packages. Mirror that here.
REPO_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ocr import MangaOcrService  # noqa: E402


def test_recognize_returns_a_string():
    """The wrapper should always return a string, never raise."""
    svc = MangaOcrService.instance()
    out = svc.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
    assert isinstance(out, str)


def test_none_input_returns_empty_string():
    """None / empty inputs are short-circuited before hitting the model."""
    svc = MangaOcrService.instance()
    assert svc.recognize(None) == ""  # type: ignore[arg-type]


def test_padding_does_not_crash():
    svc = MangaOcrService.instance()
    img = np.full((40, 120, 3), 255, dtype=np.uint8)
    out = svc.recognize(img, padding=20)
    assert isinstance(out, str)


@pytest.mark.skipif(
    not Path("/Users/matheusmedrado/Library/Caches/huggingface/hub").exists()
    and not Path.home().joinpath(".cache", "huggingface", "hub").exists(),
    reason="HuggingFace cache not present; skipping real inference test",
)
def test_recognize_white_image_returns_string():
    """If the model is already downloaded, recognize a blank-ish crop."""
    svc = MangaOcrService.instance()
    if not svc.is_available():
        pytest.skip("manga-ocr model not loaded")
    blank = np.full((80, 240, 3), 255, dtype=np.uint8)
    out = svc.recognize(blank)
    assert isinstance(out, str)
