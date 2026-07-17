"""Text-region segmentation (Labs 02, 06, 07, 08).

Pipeline:
    gray / ink mask
        -> Otsu threshold (Lab 06)
        -> Mathematical morphology to clean the binary mask (Lab 07)
        -> Connected components (Lab 02)
        -> Optional watershed pass (Lab 08) for components that look like
           multiple touching text regions
        -> Group components into text lines (or vertical columns) for the
           hover UI to reason about.

The output of `detect_text_regions` is a list of `TextRegion`s in original
image coordinates. Each region has a stable integer `id` so the frontend can
address it without depending on its position.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TextRegion:
    """A bounding box in the original image, in (x, y, w, h) format."""
    x: int
    y: int
    w: int
    h: int
    id: int = -1
    inverted: bool = False

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "x": int(self.x),
            "y": int(self.y),
            "w": int(self.w),
            "h": int(self.h),
        }


# Module-level counter so each detection pass produces unique ids.
_id_counter = 0


def _next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter


# ---------------------------------------------------------------------------
# Lab 06 — Otsu threshold
# ---------------------------------------------------------------------------

def otsu_threshold(gray_or_mask: np.ndarray,
                   invert: bool | None = None) -> np.ndarray:
    """Automatic Otsu threshold on a grayscale image or already-binary mask.

    If the input is already binary (only 0/255) this is essentially a no-op
    and the function returns a copy. Otherwise it computes Otsu's threshold
    and binarizes.

    `invert=None` chooses automatically: if the input has more bright than
    dark pixels we flip so that ink is 255 in the output.
    """
    if gray_or_mask.ndim != 2:
        raise ValueError("otsu_threshold espera imagem 2D.")
    if set(np.unique(gray_or_mask).tolist()).issubset({0, 255}):
        binary = gray_or_mask.copy()
    else:
        thr, binary = cv2.threshold(
            gray_or_mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    if invert is None:
        # Convention: ink (text) is white in the mask. Flip if the input
        # appears to be the opposite.
        frac_white = float(np.count_nonzero(binary)) / binary.size
        if frac_white > 0.5:
            binary = cv2.bitwise_not(binary)
    elif invert:
        binary = cv2.bitwise_not(binary)
    return binary


# ---------------------------------------------------------------------------
# Lab 07 — morphology
# ---------------------------------------------------------------------------

def morphology_cleanup(binary: np.ndarray,
                       open_k: int = 3,
                       close_k: int = 5) -> np.ndarray:
    """Clean a binary mask with opening + closing (Lab 07).

    Opening removes single-pixel noise; closing fills tiny holes inside ink
    strokes. The kernel sizes are deliberately small to avoid merging nearby
    text.
    """
    if binary.ndim != 2:
        raise ValueError("morphology_cleanup espera imagem 2D.")
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (open_k, open_k))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))
    out = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, close_kernel)
    return out


# ---------------------------------------------------------------------------
# Lab 02 — connected components
# ---------------------------------------------------------------------------

def connected_components(binary: np.ndarray, min_area: int = 30,
                         max_area: int | None = None,
                         min_aspect: float = 0.05,
                         max_aspect: float = 20.0) -> list[TextRegion]:
    """Label connected components and return the surviving ones as TextRegion.

    Filters:
      - drops anything smaller than `min_area` (Lab 02);
      - optionally drops anything larger than `max_area`;
      - drops components with extreme aspect ratios that are almost certainly
        not text (very thin lines or huge solid blocks).
    """
    if binary.ndim != 2:
        raise ValueError("connected_components espera imagem 2D.")
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    regions: list[TextRegion] = []
    for label in range(1, n_labels):  # skip background
        x, y, w, h, area = stats[label]
        if area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue
        aspect = max(w, h) / max(1, min(w, h))
        if aspect < (1.0 / max_aspect) or aspect > max_aspect:
            continue
        regions.append(TextRegion(int(x), int(y), int(w), int(h), _next_id()))
    return regions


# ---------------------------------------------------------------------------
# Lab 08 — watershed for touching text
# ---------------------------------------------------------------------------

def _looks_like_text_blob(region: TextRegion, binary: np.ndarray,
                          min_fill: float = 0.15,
                          max_fill: float = 0.85) -> bool:
    """Heuristic: a blob that is mostly filled with ink is probably several
    merged characters/lines and is a good candidate for watershed splitting."""
    x, y, w, h = region.x, region.y, region.w, region.h
    crop = binary[y:y + h, x:x + w]
    if crop.size == 0:
        return False
    fill = float(np.count_nonzero(crop)) / crop.size
    return min_fill < fill < max_fill


def watershed_split(binary: np.ndarray, region: TextRegion) -> list[TextRegion]:
    """Apply distance-transform + watershed to a single component (Lab 08).

    Returns the original region if watershed could not produce new ones.
    """
    x, y, w, h = region.x, region.y, region.w, region.h
    crop = binary[y:y + h, x:x + w]
    if crop.size == 0 or not _looks_like_text_blob(region, binary):
        return [region]

    sure_bg = cv2.dilate(crop, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
                         iterations=2)
    dist = cv2.distanceTransform(crop, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.5 * dist.max(), 255, 0)
    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    color = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    markers = cv2.watershed(color, markers)

    out: list[TextRegion] = []
    for m in np.unique(markers):
        if m <= 1:  # background / boundary
            continue
        mask = (markers == m).astype(np.uint8) * 255
        # Snap to the original crop's bounding box to drop the boundary
        # pixels that watershed marks as -1.
        ys, xs = np.where(mask > 0)
        if len(xs) < 8:
            continue
        x0, y0 = int(xs.min()), int(ys.min())
        x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
        out.append(TextRegion(x + x0, y + y0, x1 - x0, y1 - y0, _next_id()))
    if not out:
        return [region]
    return out


# ---------------------------------------------------------------------------
# Speech-bubble detection (Labs 02, 06, 07)
# ---------------------------------------------------------------------------

def _enclosed_uniform_regions(gray: np.ndarray, bright: bool,
                              thresh: int,
                              min_area_frac: float,
                              max_area_frac: float,
                              min_extent: float,
                              min_solidity: float,
                              min_interior_frac: float,
                              ) -> list[TextRegion]:
    """Find enclosed, uniformly-colored regions (bubble interiors).

    A speech bubble is, classically:
      - a large connected region of near-white (or near-black) pixels,
      - with a mostly convex, blob-like shape (extent + solidity),
      - whose interior is *uniformly* that color (this is what separates a
        bubble from an art mass: art has texture inside, bubbles do not).
    """
    h_img, w_img = gray.shape[:2]
    page_area = h_img * w_img

    if bright:
        m = (gray >= thresh).astype(np.uint8) * 255
    else:
        m = (gray <= thresh).astype(np.uint8) * 255
    # Close small gaps in the bubble outline (anti-aliasing breaks, tails).
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(m)
    out: list[TextRegion] = []
    for label in range(1, n_labels):
        x, y, w, h, area = stats[label]
        if not (min_area_frac * page_area <= area <= max_area_frac * page_area):
            continue
        extent = area / max(1, w * h)
        if extent < min_extent:
            continue
        comp = (labels[y:y + h, x:x + w] == label).astype(np.uint8) * 255
        contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        hull = cv2.convexHull(contours[0])
        hull_area = cv2.contourArea(hull)
        if hull_area <= 0:
            continue
        solidity = area / hull_area
        if solidity < min_solidity:
            continue
        # Interior uniformity: fraction of the bbox dominated by the
        # bubble color. Bubbles are plain inside; art is not.
        gray_crop = gray[y:y + h, x:x + w]
        if bright:
            interior = float(np.count_nonzero(gray_crop >= thresh)) / (w * h)
        else:
            interior = float(np.count_nonzero(gray_crop <= thresh)) / (w * h)
        if interior < min_interior_frac:
            continue
        out.append(TextRegion(int(x), int(y), int(w), int(h), _next_id(),
                              inverted=not bright))
    return out


def find_speech_bubbles(gray: np.ndarray,
                        min_area_frac: float = 0.002,
                        max_area_frac: float = 0.20,
                        min_extent: float = 0.30,
                        min_solidity: float = 0.55,
                        white_thresh: int = 230,
                        black_thresh: int = 25,
                        white_interior: float = 0.60,
                        black_interior: float = 0.72,
                        ) -> list[TextRegion]:
    """Detect white and black (inverted-text) speech bubbles on a page.

    Returns bubble-level `TextRegion`s — exactly the granularity manga-ocr
    was trained on, and exactly what the hover UI wants. Regions detected on
    dark interiors are flagged `inverted=True` so the OCR stage can invert
    the crop (white text on black bubble).
    """
    bubbles = _enclosed_uniform_regions(
        gray, bright=True, thresh=white_thresh,
        min_area_frac=min_area_frac, max_area_frac=max_area_frac,
        min_extent=min_extent, min_solidity=min_solidity,
        min_interior_frac=white_interior,
    )
    dark = _enclosed_uniform_regions(
        gray, bright=False, thresh=black_thresh,
        min_area_frac=min_area_frac, max_area_frac=max_area_frac,
        min_extent=min_extent, min_solidity=min_solidity,
        min_interior_frac=black_interior,
    )
    out = bubbles + dark
    # Rough reading order: top-to-bottom, right-to-left (manga).
    out.sort(key=lambda r: (r.y, -r.x))
    return out


# ---------------------------------------------------------------------------
# Group components into text lines (or vertical columns)
# ---------------------------------------------------------------------------

def cluster_lines(regions: list[TextRegion], gap_factor: float = 0.7,
                  vertical: bool = False) -> list[list[TextRegion]]:
    """Greedy clustering of components into lines.

    Components whose y-overlap (for horizontal text) or x-overlap (for
    vertical text) is large enough are merged into the same line. `gap_factor`
    is the fraction of the smaller region's height (or width) that must be
    overlapping for the pair to be grouped.

    A line is returned as a list of `TextRegion` objects sorted along the
    reading direction: left→right for horizontal, top→bottom for vertical.
    """
    if not regions:
        return []

    def overlap(a: int, b: int, c: int, d: int) -> int:
        return max(0, min(b, d) - max(a, c))

    if vertical:
        # group by x-overlap, sort by y.
        def key(r: TextRegion) -> tuple[int, int]:
            return (r.x, r.y)
        primary_axis = lambda r: (r.x, r.x + r.w)
        secondary_axis = lambda r: (r.y, r.y + r.h)
    else:
        # group by y-overlap, sort by x.
        def key(r: TextRegion) -> tuple[int, int]:
            return (r.y, r.x)
        primary_axis = lambda r: (r.y, r.y + r.h)
        secondary_axis = lambda r: (r.x, r.x + r.w)

    # Sort by primary axis, then secondary, for stable clustering.
    ordered = sorted(regions, key=key)
    lines: list[list[TextRegion]] = []
    current: list[TextRegion] = [ordered[0]]
    current_span = primary_axis(ordered[0])

    for r in ordered[1:]:
        span = primary_axis(r)
        ov = overlap(*current_span, *span)
        ref = min(span[1] - span[0], current_span[1] - current_span[0])
        if ref > 0 and ov / ref >= gap_factor:
            current.append(r)
            current_span = (min(current_span[0], span[0]),
                            max(current_span[1], span[1]))
        else:
            lines.append(current)
            current = [r]
            current_span = span
    lines.append(current)

    # Sort within each line along the reading direction.
    for line in lines:
        if vertical:
            line.sort(key=lambda r: r.y)
        else:
            line.sort(key=lambda r: r.x)
    return lines


# ---------------------------------------------------------------------------
# Top-level: from page to text regions
# ---------------------------------------------------------------------------

def detect_text_regions(gray: np.ndarray, mask: np.ndarray | None = None,
                        min_area: int = 80,
                        use_watershed: bool = False,
                        vertical: bool = False,
                        min_fill: float = 0.0,
                        max_fill: float = 1.0,
                        max_page_fraction: float = 0.30,
                        merge_kernel: tuple[int, int] | None = None,
                        remove_rules: bool = False,
                        rule_len: int | None = None,
                        ) -> list[TextRegion]:
    """Run the full segmentation pipeline on a (resized) gray page.

    Steps (each one a lab technique):
      1. Binarize (Otsu, Lab 06) — from `mask` (color, Lab 09) or `gray`.
      2. Morphology cleanup (Lab 07).
      3. **Merge dilation** (Lab 07): a wide-ish rectangular kernel merges
         strokes/characters into text-line blocks without merging separate
         lines or neighboring bubbles.
      4. Connected components (Lab 02) on the merged mask.
      5. Filters:
         - drop blocks covering more than `max_page_fraction` of the page
           (page frames/panels);
         - drop blocks that touch the image border AND span more than half
           the page in one axis (scan borders, panel frames);
         - drop blocks whose *ink fill ratio* (in the un-dilated binary) is
           outside [`min_fill`, `max_fill`]. Hollow bubble/panel outlines have
           very low fill; solid art/screentone blocks have very high fill.
      6. Optional watershed (Lab 08) on the surviving blobs.
      7. Sort in rough reading order.

    Parameters
    ----------
    gray, mask, min_area : as before.
    use_watershed : off by default; enable to split dense merged blobs.
    vertical : reading-order hint used only for the final sort.
    min_fill, max_fill : ink-density filter range (0..1). Defaults keep
        everything (unit-test friendly); the app passes tighter values.
    """
    if mask is not None and mask.shape[:2] != gray.shape[:2]:
        mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    binary = morphology_cleanup(
        otsu_threshold(mask if mask is not None else gray)
    )

    h_img, w_img = gray.shape[:2]
    page_area = h_img * w_img

    work = binary
    if remove_rules:
        # Rule-line removal (Lab 07): morphological opening with long, thin
        # structuring elements keeps only strokes with a continuous straight
        # run of `rule_len` pixels — bubble outlines, panel frames, divider
        # lines, speedlines. Text strokes are much shorter and survive.
        # This is the classical document-analysis trick.
        if rule_len is None:
            rule_len = max(30, w_img // 40)
        horiz = cv2.morphologyEx(
            work, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (rule_len, 1)),
        )
        vert = cv2.morphologyEx(
            work, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, rule_len)),
        )
        rules = cv2.bitwise_or(horiz, vert)
        # Grow the rule mask slightly so anti-aliased edges go away too.
        rules = cv2.dilate(rules, np.ones((3, 3), np.uint8), iterations=1)
        work = cv2.bitwise_and(work, cv2.bitwise_not(rules))

    if merge_kernel is None:
        kx = max(3, w_img // 90)
        ky = max(3, h_img // 120)
        merge_kernel = (kx, ky)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, merge_kernel)
    merged = cv2.dilate(work, kernel, iterations=1)

    blocks = connected_components(merged, min_area=min_area)

    kept: list[TextRegion] = []
    for b in blocks:
        block_area = b.w * b.h
        if block_area > max_page_fraction * page_area:
            continue
        touches_border = (b.x <= 1 or b.y <= 1
                          or b.x + b.w >= w_img - 1 or b.y + b.h >= h_img - 1)
        if touches_border and (b.w > 0.5 * w_img or b.h > 0.5 * h_img):
            continue
        crop = work[b.y:b.y + b.h, b.x:b.x + b.w]
        fill = float(np.count_nonzero(crop)) / max(1, block_area)
        if not (min_fill <= fill <= max_fill):
            continue
        kept.append(b)

    if use_watershed:
        split: list[TextRegion] = []
        for b in kept:
            split.extend(watershed_split(binary, b))
        kept = split

    # Rough reading order: top-to-bottom; right-to-left for vertical text.
    kept.sort(key=lambda r: (r.y, -r.x if vertical else r.x))
    return kept
