from __future__ import annotations

import numpy as np

from pipeline.ocr import char_segment
from pipeline.ocr.bitmap import BitmapClassifier
from pipeline.ocr.templates import TemplateDB


class TemplateClassifier:
    def __init__(self, db: TemplateDB, grid: int = 8, top_k: int = 80):
        if db.bitmaps_packed is None:
            raise ValueError(
                "Banco de templates sem bitmaps. Regere o banco com "
                "python backend/pipeline/ocr/build_templates.py"
            )
        self.db = db
        self.classifier = BitmapClassifier(
            db.bitmaps_packed, db.ref_pixels, db.ref_halos, db.labels, top_k=top_k
        )

    def classify(self, glyph: np.ndarray, k: int = 3, alpha: float | None = None) -> tuple[str, float]:
        return self.classifier.classify(glyph, k=k, alpha=alpha)

    def ocr_region(self, gray: np.ndarray, k: int = 3, alpha: float | None = None) -> dict:
        glyphs = char_segment.segment_glyphs(gray)
        chars: list[str] = []
        details: list[dict] = []
        for g in glyphs:
            char, conf = self.classify(g.image, k, alpha)
            chars.append(char)
            details.append({"x": g.x, "y": g.y, "w": g.w, "h": g.h, "char": char, "conf": conf})
        return {"text": "".join(chars), "glyphs": details, "count": len(chars)}
