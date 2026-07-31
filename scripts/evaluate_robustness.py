#!/usr/bin/env python3
"""Avalia quanto a PDI recupera o OCR após degradações controladas."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ocr import MangaOcrService
from backend.pipeline.detection import detect_blocks, get_detector
from backend.pipeline.metrics import evaluate_regions
from backend.pipeline.robustness import DEGRADATIONS, LABELS, degradation_triplet


def scaled_truth(page_data: dict, image: np.ndarray) -> list[dict]:
    width = float(page_data.get("annotation_width", image.shape[1]))
    height = float(page_data.get("annotation_height", image.shape[0]))
    sx, sy = image.shape[1] / width, image.shape[0] / height
    boxes = page_data.get("rough_boxes", {})
    output = []
    for region in page_data.get("regions", []):
        box = boxes.get(region.get("bubble_id"))
        if box is None:
            continue
        x, y, w, h = box
        output.append({**region, "x": round(x * sx), "y": round(y * sy),
                       "w": round(w * sx), "h": round(h * sy)})
    return output


def _tile(label: str, image: np.ndarray, width: int = 360,
          height: int = 180) -> np.ndarray:
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    scale = min((width - 20) / image.shape[1], (height - 42) / image.shape[0])
    w = max(1, int(round(image.shape[1] * scale)))
    h = max(1, int(round(image.shape[0] * scale)))
    resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    x, y = (width - w) // 2, 34 + (height - 40 - h) // 2
    canvas[y:y + h, x:x + w] = resized
    cv2.putText(canvas, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (25, 25, 25), 1, cv2.LINE_AA)
    return canvas


def evidence_panel(original: np.ndarray, degraded: np.ndarray,
                   restored: np.ndarray, label: str) -> np.ndarray:
    return np.hstack([
        _tile("Original limpo", original),
        _tile(f"{label}: sem PDI", degraded),
        _tile(f"{label}: com PDI", restored),
    ])


def _variant_names() -> list[str]:
    names = ["clean"]
    for kind in DEGRADATIONS:
        names.extend((f"{kind}_degraded", f"{kind}_restored"))
    return names


def _summary(metrics) -> dict:
    associated = [metric for metric in metrics if metric.prediction_id is not None]
    return {
        "truth": len(metrics),
        "associated": len(associated),
        "cer_sum_all": float(sum(metric.cer for metric in metrics)),
        "cer_sum_associated": float(sum(metric.cer for metric in associated)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", nargs="+", default=["08.png", "09.png", "10.png", "11.png"])
    parser.add_argument("--truth", type=Path, default=ROOT / "backend/data/ground_truth/sample_08_11_transcripts.json")
    parser.add_argument("--output", type=Path, default=ROOT / "presentation_artifacts/robustness")
    args = parser.parse_args()

    truth_document = json.loads(args.truth.read_text(encoding="utf-8"))
    truth_pages = truth_document.get("pages", truth_document)
    detector = get_detector(device="cpu")
    if not detector.available:
        raise RuntimeError("comictextdetector.pt não encontrado")
    ocr = MangaOcrService.instance()
    args.output.mkdir(parents=True, exist_ok=True)

    page_rows = []
    totals = defaultdict(lambda: {"truth": 0, "associated": 0,
                                  "cer_sum_all": 0.0, "cer_sum_associated": 0.0})
    evidence_written = set()

    for page_number, page_name in enumerate(args.pages):
        image = cv2.imread(str(ROOT / "sample" / page_name), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(ROOT / "sample" / page_name)
        page_truth = next(item for item in truth_pages if item.get("page") == page_name)
        expected = scaled_truth(page_truth, image)
        blocks = detect_blocks(image, detector=detector, mode="baseline")
        predictions = {name: [] for name in _variant_names()}

        for block in blocks:
            texts = {name: "" for name in predictions}
            for line_index, crop in enumerate(block.crops):
                texts["clean"] += ocr.recognize(crop)
                seed = page_number * 10000 + block.id * 100 + line_index
                for kind in DEGRADATIONS:
                    original, degraded, restored = degradation_triplet(crop, kind, seed)
                    texts[f"{kind}_degraded"] += ocr.recognize(degraded)
                    texts[f"{kind}_restored"] += ocr.recognize(restored)
                    if kind not in evidence_written:
                        panel = evidence_panel(original, degraded, restored, LABELS[kind])
                        cv2.imwrite(str(args.output / f"evidence_{kind}.png"), panel)
                        evidence_written.add(kind)
            for variant, text in texts.items():
                predictions[variant].append({**block.to_dict(), "text": text})

        for variant, records in predictions.items():
            summary = _summary(evaluate_regions(records, expected))
            row = {"page": page_name, "variant": variant, **summary}
            page_rows.append(row)
            for key, value in summary.items():
                totals[variant][key] += value
        print(f"{page_name}: {len(blocks)} caixas avaliadas")

    aggregate = []
    for variant in _variant_names():
        item = totals[variant]
        aggregate.append({
            "variant": variant,
            "truth": item["truth"],
            "associated": item["associated"],
            "cer_all": item["cer_sum_all"] / max(1, item["truth"]),
            "cer_associated": item["cer_sum_associated"] / max(1, item["associated"]),
        })

    result = {"parameters": {
        "low_contrast_factor": 0.05,
        "gaussian_sigma": 80.0,
        "salt_pepper_density": 0.10,
    }, "pages": page_rows, "aggregate": aggregate}
    (args.output / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    by_variant = {row["variant"]: row for row in aggregate}
    report = [
        "# Robustez do OCR com PDI", "",
        "Detecção fixa; a degradação é aplicada somente aos mesmos recortes enviados ao OCR.", "",
        "| Cenário | Sem PDI | Com PDI | Redução absoluta do CER |", "|---|---:|---:|---:|",
    ]
    for kind in DEGRADATIONS:
        degraded = by_variant[f"{kind}_degraded"]["cer_associated"]
        restored = by_variant[f"{kind}_restored"]["cer_associated"]
        report.append(f"| {LABELS[kind]} | {degraded:.3f} | {restored:.3f} | {degraded - restored:+.3f} |")
    clean = by_variant["clean"]
    report.extend(["", f"Cobertura fixa: {clean['associated']}/{clean['truth']} anotações associadas.",
                   f"CER do material limpo: {clean['cer_associated']:.3f}."])
    (args.output / "report.md").write_text("\n".join(report), encoding="utf-8")

    print("\n".join(report))
    print(f"Artefatos: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
