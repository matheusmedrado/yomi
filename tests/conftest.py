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

FONT_PATH = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"


def has_font() -> bool:
    return os.path.exists(FONT_PATH)


@pytest.fixture(scope="session")
def font() -> ImageFont.FreeTypeFont:
    if not has_font():
        pytest.skip("Fonte japonesa nao disponivel neste ambiente")
    return ImageFont.truetype(FONT_PATH, 64, index=0)


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    if not has_font():
        pytest.skip("Fonte japonesa nao disponivel neste ambiente")
    from pipeline.ocr.build_templates import build_templates

    db_path = tmp_path_factory.mktemp("db") / "templates.pkl"
    build_templates(db_path=str(db_path))
    from pipeline.ocr.templates import TemplateDB

    return TemplateDB.load(db_path=str(db_path))


def render_text(text: str, font: ImageFont.FreeTypeFont, size: int = 64) -> np.ndarray:
    img = Image.new("L", (len(text) * size + 40, size + 40), 255)
    ImageDraw.Draw(img).text((20, 20), text, font=font, fill=0)
    return np.array(img, dtype=np.uint8)
