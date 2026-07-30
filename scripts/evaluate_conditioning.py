#!/usr/bin/env python3
"""Create local visual evidence for the hybrid detector + PDI OCR pipeline.

Examples
--------
python scripts/evaluate_conditioning.py sample.cbz sampleTranslated.cbz
python scripts/evaluate_conditioning.py sample/02.png sampleTranslated/02.png

The English input is a geometry/reference aid only.  This script intentionally
does not infer character-level OCR accuracy from it: the report says whether a
Japanese detector region visually corresponds to its aligned English page.
Outputs default to ``presentation_artifacts/`` (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ocr import MangaOcrService
from backend.pipeline.detection import DETECTION_MODES, detect_blocks, get_detector
from backend.pipeline.metrics import evaluate_regions


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _natural_key(name: str) -> list[object]:
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", name)]


def load_pages(source: Path) -> list[tuple[str, np.ndarray]]:
    """Load either one image or all image members in a CBZ/ZIP."""
    if source.suffix.lower() in IMAGE_EXTENSIONS:
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"could not read image: {source}")
        return [(source.name, image)]
    with zipfile.ZipFile(source) as archive:
        names = sorted((n for n in archive.namelist()
                        if Path(n).suffix.lower() in IMAGE_EXTENSIONS), key=_natural_key)
        pages: list[tuple[str, np.ndarray]] = []
        for name in names:
            data = np.frombuffer(archive.read(name), dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if image is not None:
                pages.append((Path(name).name, image))
    if not pages:
        raise ValueError(f"no readable image pages in {source}")
    return pages


def scaled_truth(page_data: dict, image: np.ndarray) -> list[dict]:
    """Scale the supplied annotation canvas to the source PNG dimensions."""
    boxes = page_data.get("rough_boxes", {})
    width = float(page_data.get("annotation_width", image.shape[1]))
    height = float(page_data.get("annotation_height", image.shape[0]))
    sx, sy = image.shape[1] / width, image.shape[0] / height
    out = []
    for region in page_data.get("regions", []):
        box = boxes.get(region.get("bubble_id"))
        if box is None:
            continue
        x, y, w, h = box
        out.append({**region, "x": round(x * sx), "y": round(y * sy),
                    "w": round(w * sx), "h": round(h * sy)})
    return out


def _fit_height(image: np.ndarray, height: int) -> np.ndarray:
    if image.shape[0] == height:
        return image
    width = max(1, int(round(image.shape[1] * height / image.shape[0])))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def page_reference(japanese: np.ndarray, english: np.ndarray) -> np.ndarray:
    height = min(1200, max(japanese.shape[0], english.shape[0]))
    jp, en = _fit_height(japanese, height), _fit_height(english, height)
    gap = np.full((height, 16, 3), 245, dtype=np.uint8)
    board = np.concatenate([jp, gap, en], axis=1)
    cv2.putText(board, "Japanese source", (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 0, 220), 2, cv2.LINE_AA)
    cv2.putText(board, "English aligned reference", (jp.shape[1] + 28, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2, cv2.LINE_AA)
    return board


def crop_board(result) -> np.ndarray:
    """Raw detector line beside its final PDI crop(s)."""
    raw = result.raw
    final = result.crops[0] if len(result.crops) == 1 else np.concatenate(result.crops, axis=1)
    height = max(raw.shape[0], final.shape[0])
    raw, final = _fit_height(raw, height), _fit_height(final, height)
    gap = np.full((height, 12, 3), 245, dtype=np.uint8)
    board = np.concatenate([raw, gap, final], axis=1)
    cv2.putText(board, "raw detector crop", (4, 16), cv2.FONT_HERSHEY_SIMPLEX,
                0.45, (0, 0, 220), 1, cv2.LINE_AA)
    cv2.putText(board, "PDI OCR crop", (raw.shape[1] + 16, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 220), 1, cv2.LINE_AA)
    return board


def truth_overlay(image: np.ndarray, truth: list[dict]) -> np.ndarray:
    """Make approximate transcript geometry inspectable during calibration."""
    out = image.copy()
    for index, region in enumerate(truth, 1):
        x, y, w, h = (int(region[key]) for key in ("x", "y", "w", "h"))
        cv2.rectangle(out, (x, y), (x + w, y + h), (220, 30, 30), 3)
        cv2.putText(out, str(index), (x + 3, max(18, y + 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 30, 30), 2, cv2.LINE_AA)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("japanese", type=Path, help="Japanese page image or CBZ")
    parser.add_argument("english", type=Path, help="aligned English page image or CBZ")
    parser.add_argument("--output", type=Path, default=ROOT / "presentation_artifacts")
    parser.add_argument("--pages", type=int, default=3, help="maximum paired pages to evaluate")
    parser.add_argument("--regions", type=int, default=3, help="crop boards per page")
    parser.add_argument("--skip-ocr", action="store_true", help="do not run manga-ocr")
    parser.add_argument("--mode", choices=DETECTION_MODES, default="hybrid",
                        help="baseline, hybrid, or pdi_only")
    parser.add_argument("--ground-truth", type=Path,
                        help="JSON transcript annotations, optionally wrapped as {pages: [...]}")
    args = parser.parse_args()

    jp_pages, en_pages = load_pages(args.japanese), load_pages(args.english)
    count = min(args.pages, len(jp_pages), len(en_pages))
    if count == 0:
        raise ValueError("the two inputs have no paired pages")
    args.output.mkdir(parents=True, exist_ok=True)
    ground_truth = None
    if args.ground_truth:
        ground_truth = json.loads(args.ground_truth.read_text(encoding="utf-8"))
        if isinstance(ground_truth, dict):
            ground_truth = ground_truth.get("pages", [ground_truth])
    detector = None
    if args.mode != "pdi_only":
        detector = get_detector(device="cpu")
        if not detector.available:
            raise RuntimeError("comic-text-detector model unavailable; cannot evaluate regions")
    ocr = MangaOcrService.instance()
    report = [
        f"# {args.mode} conditioning evaluation",
        "",
        "English pages are alignment evidence only; no character-level OCR accuracy is claimed without Japanese transcripts.",
        "",
    ]
    total_regions = conditioned = normalized = raw = baseline_raw = nonempty_ocr = 0
    for page_index in range(count):
        page_name, jp = jp_pages[page_index]
        _english_name, en = en_pages[page_index]
        cv2.imwrite(str(args.output / f"page_{page_index + 1:03d}_reference.png"), page_reference(jp, en))
        truth_page = next((p for p in ground_truth or [] if p.get("page") == page_name), None)
        if truth_page is not None:
            cv2.imwrite(str(args.output / f"page_{page_index + 1:03d}_ground_truth.png"),
                        truth_overlay(jp, scaled_truth(truth_page, jp)))
        blocks = detect_blocks(jp, detector=detector, mode=args.mode)
        total_regions += len(blocks)
        page_nonempty = 0
        report.extend([f"## Page {page_index + 1}", "", f"- Detected regions: {len(blocks)}"])
        for block in blocks:
            if args.mode == "baseline":
                baseline_raw += len(block.crops)
                continue
            for result in block.conditioning:
                status = result.fallback or "conditioned"
                conditioned += status == "conditioned"
                normalized += status == "normalized"
                raw += status == "raw_fallback"
        for block in blocks[:args.regions]:
            for line_index, result in enumerate(block.conditioning):
                out = args.output / f"page_{page_index + 1:03d}_region_{block.id:02d}_line_{line_index:02d}.png"
                cv2.imwrite(str(out), crop_board(result))
        predicted = [{**block.to_dict(), "text": ""} for block in blocks]
        run_ocr = not args.skip_ocr
        if run_ocr:
            for record, block in zip(predicted, blocks):
                text = "".join(ocr.recognize(crop) for crop in block.crops)
                if text:
                    page_nonempty += 1
                record["text"] = text
        nonempty_ocr += page_nonempty
        if truth_page is not None:
            region_metrics = evaluate_regions(predicted, scaled_truth(truth_page, jp))
            matched = sum(metric.prediction_id is not None for metric in region_metrics)
            mean_cer = sum(metric.cer for metric in region_metrics) / max(1, len(region_metrics))
            report.extend([
                f"- Ground-truth regions: {len(region_metrics)}",
                f"- Ground-truth matches (IoU/containment≥0.10): {matched}",
                f"- Mean end-to-end CER: {mean_cer:.3f}",
            ])
        report.extend([
            f"- Conditioned line crops shown: {sum(len(b.conditioning) for b in blocks[:args.regions])}",
            f"- Non-empty OCR regions: {page_nonempty}" if run_ocr else "- OCR skipped by request.",
            "- Use the side-by-side reference to inspect bubble/region correspondence and intended dialogue meaning.",
            "",
        ])
    report.extend([
        "## Totals", "",
        f"- Detected regions: {total_regions}",
        f"- Valid conditioned lines: {conditioned}",
        f"- Normalization fallbacks: {normalized}",
        f"- Raw fallbacks (unexpected errors only): {raw}",
        f"- Baseline raw OCR crops: {baseline_raw}",
        f"- Non-empty OCR regions: {nonempty_ocr}" if not args.skip_ocr else "- Non-empty OCR regions: skipped",
        "",
        "The PDI stage normalizes contrast, builds a classical ink mask for geometry, validates connected components, tightens usable extent, and splits long horizontalized lines. In hybrid and pdi_only modes, manga-ocr receives the normalized grayscale crop; baseline intentionally receives raw detector crops.",
    ])
    (args.output / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {args.output / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
