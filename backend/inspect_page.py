from __future__ import annotations

import os
import sys

import cv2
import numpy as np
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.preprocess import to_grayscale, resize_longest_edge, clahe_equalize, denoise
from pipeline.segmentation import detect_text_regions
from pipeline.ocr.templates import TemplateDB
from pipeline.ocr.classifier import TemplateClassifier
from language import to_reading


def _load_image(path: str) -> np.ndarray:
    if path.lower().endswith(".cbz"):
        z = zipfile.ZipFile(path)
        name = z.namelist()[int(os.environ.get("CBZ_PAGE", "0"))]
        data = np.frombuffer(z.read(name), np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    return cv2.imread(path, cv2.IMREAD_COLOR)


def inspect(path: str, min_w: int = 35, min_h: int = 28, max_aspect: int = 6, max_regions: int = 60) -> None:
    img = _load_image(path)
    if img is None:
        print(f"Nao foi possivel carregar: {path}")
        return
    gray = denoise(clahe_equalize(resize_longest_edge(to_grayscale(img), 1600)))
    regs = detect_text_regions(gray)
    print(f"{os.path.basename(path)}: {len(regs)} regioes detectadas")

    db = TemplateDB.load()
    clf = TemplateClassifier(db)
    shown = 0
    for r in regs:
        if r.w < min_w or r.h < min_h:
            continue
        if max(r.w, r.h) / min(r.w, r.h) > max_aspect:
            continue
        region = gray[r.y : r.y + r.h, r.x : r.x + r.w]
        res = clf.ocr_region(region, k=3)
        if res["count"] < 1:
            continue
        reading = to_reading(res["text"])
        conf = sum(g["conf"] for g in res["glyphs"]) / res["count"]
        print(
            f"  ({r.x:4},{r.y:4},{r.w:4},{r.h:4}) -> '{res['text']}' "
            f"| furigana: {reading['furigana']} | romaji: {reading['romaji']} | conf: {conf:.2f}"
        )
        shown += 1
        if shown >= max_regions:
            break


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        samples = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "samples")
        files = sorted(
            f for f in os.listdir(samples)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".cbz"))
        )
        if not files:
            print("Nenhuma imagem em backend/data/samples/. Adicione as paginas JP la.")
            sys.exit(0)
        target = os.path.join(samples, files[0])
    inspect(target)
