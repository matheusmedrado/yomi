from __future__ import annotations

import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def render_text(text: str, font: ImageFont.FreeTypeFont, size: int = 64) -> np.ndarray:
    img = Image.new("L", (len(text) * size + 40, size + 40), 255)
    ImageDraw.Draw(img).text((20, 20), text, font=font, fill=0)
    return np.array(img, dtype=np.uint8)
