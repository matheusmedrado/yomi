from __future__ import annotations

import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

FONT_PATH = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"

GROUND_TRUTH = [
    "こんにちは", "ありがとう", "さようなら", "おはよう", "いただきます",
    "日本語", "カタカナ", "サクラ", "トウキョウ", "ユウトウ",
    "東京です", "勉強します", "読み方", "話します", "行きます",
    "学生", "先生", "友達", "日本語の本", "水を飲む",
    "山と川", "白い猫", "赤い花", "大きい木", "小さい鳥",
    "あいうえお", "かきくけこ", "さしすせそ", "たちつてと", "なにぬねの",
]

SIZES = [48, 64, 80]
ROTATIONS = [0, -3, 3]
NOISE = [0.0, 0.05]


def _levenshtein(a: str, b: str) -> int:
    dp = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, len(b) + 1):
            cur = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[len(b)]


def _render(text: str, font: ImageFont.FreeTypeFont, size: int, angle: int, noise: float) -> np.ndarray:
    canvas = Image.new("L", (len(text) * size + 60, size + 60), 255)
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 30), text, font=font, fill=0)
    if angle != 0:
        canvas = canvas.rotate(angle, fillcolor=255)
    arr = np.array(canvas, dtype=np.uint8)
    if noise > 0:
        salt = np.random.RandomState(0).randint(0, 256, arr.shape).astype(np.uint8)
        mask = np.random.RandomState(1).random(arr.shape) < noise
        arr[mask] = salt[mask]
    return arr


def benchmark(db_path: str | None = None, verbose: bool = False) -> dict:
    from pipeline.ocr.templates import TemplateDB
    from pipeline.ocr.classifier import TemplateClassifier

    db = TemplateDB.load(db_path) if db_path else TemplateDB.load()
    clf = TemplateClassifier(db)
    font = ImageFont.truetype(FONT_PATH, 64, index=0)

    cers: list[float] = []
    exact = 0
    total = 0
    details: list[dict] = []

    for text in GROUND_TRUTH:
        best_cer = float("inf")
        best_pred = ""
        for size in SIZES:
            f = ImageFont.truetype(FONT_PATH, size, index=0)
            for angle in ROTATIONS:
                for noise in NOISE:
                    img = _render(text, f, size, angle, noise)
                    pred = clf.ocr_region(img, k=3)["text"]
                    cer = _levenshtein(text, pred) / max(1, len(text))
                    if cer < best_cer:
                        best_cer = cer
                        best_pred = pred
        cers.append(best_cer)
        total += 1
        if best_cer == 0.0:
            exact += 1
        details.append({"expected": text, "predicted": best_pred, "cer": round(best_cer, 2)})
        if verbose:
            print(f"  {text:12} -> {best_pred:12} cer={best_cer:.2f}")

    return {
        "mean_cer": float(np.mean(cers)),
        "exact_rate": exact / total,
        "samples": total,
        "details": details,
    }


if __name__ == "__main__":
    result = benchmark(verbose=True)
    print("\n=== RESUMO ===")
    print(f"Amostras: {result['samples']}")
    print(f"CER medio (menor=melhor): {result['mean_cer']:.3f}")
    print(f"Taxa de acerto exato: {result['exact_rate']:.2%}")
