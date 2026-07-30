"""Ground-truth matching and Japanese OCR metrics."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


def normalize_text(text: str) -> str:
    """Remove layout whitespace while preserving Japanese punctuation/SFX."""
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", "", text)


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein distance divided by reference character count."""
    ref, hyp = normalize_text(reference), normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, ref_char in enumerate(ref, 1):
        current = [i]
        for j, hyp_char in enumerate(hyp, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (ref_char != hyp_char),
            ))
        previous = current
    return previous[-1] / len(ref)


def bbox_iou(a: dict, b: dict) -> float:
    ax, ay, aw, ah = (int(a[k]) for k in ("x", "y", "w", "h"))
    bx, by, bw, bh = (int(b[k]) for k in ("x", "y", "w", "h"))
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    union = aw * ah + bw * bh - intersection
    return intersection / max(1, union)


def bbox_match_score(prediction: dict, truth: dict) -> float:
    """Match a text-line prediction to a larger annotated bubble fairly.

    IoU alone penalizes a correct line crop inside a speech-bubble ground-truth
    box. Use the greater of IoU and the fraction of the predicted crop covered
    by the annotation.
    """
    ax, ay, aw, ah = (int(prediction[k]) for k in ("x", "y", "w", "h"))
    bx, by, bw, bh = (int(truth[k]) for k in ("x", "y", "w", "h"))
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    return max(bbox_iou(prediction, truth), intersection / max(1, aw * ah))


@dataclass
class RegionMetric:
    truth_id: str
    prediction_id: int | None
    iou: float
    cer: float


def evaluate_regions(predictions: Iterable[dict], truth: Iterable[dict],
                     iou_threshold: float = 0.10) -> list[RegionMetric]:
    """Greedily associate each transcript box with at most one prediction."""
    predictions = list(predictions)
    used: set[int] = set()
    metrics: list[RegionMetric] = []
    for expected in truth:
        best_index, best_iou = None, 0.0
        for index, candidate in enumerate(predictions):
            if index in used:
                continue
            overlap = bbox_match_score(candidate, expected)
            if overlap > best_iou:
                best_iou, best_index = overlap, index
        if best_index is None or best_iou < iou_threshold:
            metrics.append(RegionMetric(str(expected.get("bubble_id", "")), None,
                                        best_iou, character_error_rate(expected.get("text", ""), "")))
            continue
        used.add(best_index)
        candidate = predictions[best_index]
        metrics.append(RegionMetric(
            str(expected.get("bubble_id", "")), int(candidate.get("id", best_index)),
            best_iou, character_error_rate(expected.get("text", ""), candidate.get("text", "")),
        ))
    return metrics
