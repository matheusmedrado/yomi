from __future__ import annotations

import numpy as np

from pipeline.ocr import char_segment, features
from pipeline.ocr.templates import TemplateDB

ALPHA = 1.5


class TemplateClassifier:
    def __init__(self, db: TemplateDB, grid: int = 8):
        self.db = db
        self.grid = grid
        self.zoning = np.stack(
            [features.zoning_vector(img, grid) for img in db.images]
        ).astype(np.float32)
        flat = self.db.images.reshape(len(self.db.images), -1).astype(np.float32)
        self._tpl_flat = flat
        self._tpl_norm = np.linalg.norm(flat, axis=1)

    def _correlations(self, glyph: np.ndarray) -> np.ndarray:
        q = glyph.reshape(-1).astype(np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return np.zeros(len(self.db.images), dtype=np.float32)
        return (self._tpl_flat @ q) / (self._tpl_norm * q_norm)

    def classify(self, glyph: np.ndarray, k: int = 3, alpha: float = ALPHA) -> tuple[str, float]:
        q = features.zoning_vector(glyph, self.grid)
        dists = np.abs(self.zoning - q).sum(axis=1)
        corr = self._correlations(glyph)
        score = corr - alpha * (dists / max(dists.max(), 1e-6))
        idx = int(np.argmax(score))
        confidence = max(0.0, min(1.0, (float(corr[idx]) + 1.0) / 2.0))
        return self.db.labels[idx], confidence

    def ocr_region(self, gray: np.ndarray, k: int = 3, alpha: float = ALPHA) -> dict:
        glyphs = char_segment.segment_glyphs(gray)
        chars: list[str] = []
        details: list[dict] = []
        for g in glyphs:
            char, conf = self.classify(g.image, k, alpha)
            chars.append(char)
            details.append({"x": g.x, "y": g.y, "w": g.w, "h": g.h, "char": char, "conf": conf})
        return {"text": "".join(chars), "glyphs": details, "count": len(chars)}
