from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

SIZE = 32
INNER = 30
THRESH = 140
HALO_LAYERS = 2

OCR_BASE_SCORE = 1000.0
OCR_BLACK_SCORE = 4.0
OCR_WHITE_SCORE = 4.0
OCR_TARGET_HALO_SCORES = (-1.0, -5.0, -12.0)
OCR_REFERENCE_HALO_SCORES = (-1.0, -4.0, -10.0)


def _scale(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if value <= in_min:
        return out_min
    if value >= in_max:
        return out_max
    return out_min + (out_max - out_min) * (value - in_min) / (in_max - in_min)


def _to_ink(gray: np.ndarray) -> np.ndarray:
    if gray.dtype != np.uint8:
        gray = gray.astype(np.uint8)
    if gray.max() <= 1:
        ink = gray.astype(bool)
    else:
        ink = gray < THRESH
    if ink.size > 0 and ink.mean() > 0.5:
        ink = ~ink
    return ink


def glyph_to_bitmap(gray: np.ndarray, size: int = SIZE, inner: int = INNER) -> np.ndarray:
    """Convert a glyph image to a boolean 32x32 bitmap using the kanjitomo-style
    normalization: crop to ink bounding box, fit into an ``inner`` box with an
    aspect-ratio constraint for thin characters, and center into a ``size`` box."""
    ink = _to_ink(gray)
    coords = np.argwhere(ink)
    if coords.size == 0:
        return np.zeros((size, size), dtype=bool)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    crop = ink[y0 : y1 + 1, x0 : x1 + 1]
    h, w = crop.shape
    ratio = min(h, w) / float(max(h, w))
    min_dim = int(round(_scale(ratio, 0.1, 0.4, 8, inner)))
    if w >= h:
        tw, th = inner, min_dim
    else:
        tw, th = min_dim, inner

    crop_u = (crop.astype(np.uint8)) * 255
    resized = cv2.resize(crop_u, (tw, th), interpolation=cv2.INTER_AREA)
    rb = resized >= 128

    canvas = np.zeros((size, size), dtype=bool)
    dx = (size - tw) // 2
    dy = (size - th) // 2
    canvas[dy : dy + th, dx : dx + tw] = rb
    return canvas


def build_halo_packed(bitmap: np.ndarray, layers: int = HALO_LAYERS) -> list[np.ndarray]:
    """Return ``layers`` packed (uint64, 32) halo rings (Chebyshev distance 1..layers)."""
    src = (~bitmap).astype(np.uint8)
    dist = cv2.distanceTransform(src, cv2.DIST_C, 3)
    rings = []
    for i in range(1, layers + 1):
        ring = (dist == i) & (~bitmap)
        rings.append(_pack(ring))
    return rings


def _pack(bitmap: np.ndarray) -> np.ndarray:
    cols = np.arange(bitmap.shape[1], dtype=np.uint64)
    return (bitmap.astype(np.uint64) * (np.uint64(1) << cols)[None, :]).sum(axis=1).astype(np.uint64)


def _popcount(packed: np.ndarray) -> np.ndarray:
    x = packed.astype(np.uint64)
    m1 = np.uint64(0x5555555555555555)
    m2 = np.uint64(0x3333333333333333)
    m4 = np.uint64(0x0F0F0F0F0F0F0F0F)
    x = x - ((x >> np.uint64(1)) & m1)
    x = (x & m2) + ((x >> np.uint64(2)) & m2)
    x = (x + (x >> np.uint64(4))) & m4
    x = x + (x >> np.uint64(8))
    x = x + (x >> np.uint64(16))
    x = x + (x >> np.uint64(32))
    return (x & np.uint64(0x7F)).astype(np.int64)


def translate_bitmap(bitmap: np.ndarray, ht: int, vt: int) -> np.ndarray:
    out = np.zeros_like(bitmap)
    h, w = bitmap.shape
    sy = max(0, vt)
    ey = h + min(0, vt)
    sx = max(0, ht)
    ex = w + min(0, ht)
    out[sy:ey, sx:ex] = bitmap[max(0, -vt) : min(h, h - vt), max(0, -ht) : min(w, w - ht)]
    return out


def stretch_bitmap(bitmap: np.ndarray, hs: int, vs: int, size: int = SIZE) -> np.ndarray:
    img = Image.fromarray((~bitmap).astype(np.uint8) * 255, mode="L")
    nw, nh = size + hs, size + vs
    img = img.resize((nw, nh), Image.BILINEAR)
    arr = np.array(img, dtype=np.uint8)
    canvas = np.zeros((size, size), dtype=np.uint8)
    dx = (size - nw) // 2
    dy = (size - nh) // 2
    dst_y0, dst_y1 = max(0, dy), min(size, dy + nh)
    dst_x0, dst_x1 = max(0, dx), min(size, dx + nw)
    src_y0, src_y1 = dst_y0 - dy, dst_y1 - dy
    src_x0, src_x1 = dst_x0 - dx, dst_x1 - dx
    canvas[dst_y0:dst_y1, dst_x0:dst_x1] = arr[src_y0:src_y1, src_x0:src_x1]
    return canvas >= 128


def transform_bitmap(bitmap: np.ndarray, ht: int, vt: int, hs: int, vs: int) -> np.ndarray:
    if hs != 0 or vs != 0:
        bitmap = stretch_bitmap(bitmap, hs, vs)
    if ht != 0 or vt != 0:
        bitmap = translate_bitmap(bitmap, ht, vt)
    return bitmap


def valid_transforms(size: int = SIZE, inner: int = INNER, max_steps: int = 4) -> list[tuple[int, int, int, int]]:
    margin = (size - inner) // 2
    out = []
    for ht in range(-margin, margin + 1):
        for vt in range(-margin, margin + 1):
            for hs in range(-2, 3):
                for vs in range(-2, 3):
                    if abs(ht) + abs(vt) + abs(hs) + abs(vs) > max_steps:
                        continue
                    if (abs(hs) + 1) // 2 + abs(ht) > margin:
                        continue
                    if (abs(vs) + 1) // 2 + abs(vt) > margin:
                        continue
                    out.append((ht, vt, hs, vs))
    return out


def _refined_score(
    target_packed: np.ndarray,
    target_halos: list[np.ndarray],
    target_pixels: int,
    ref_packed: np.ndarray,
    ref_halos: list[np.ndarray],
    ref_pixels: int,
) -> tuple[float, int]:
    black = int(_popcount(target_packed & ref_packed).sum())
    t_matrix = target_packed.copy()
    r_matrix = ref_packed.copy()
    t_halo = [0, 0, 0]
    r_halo = [0, 0, 0]
    for i in range(HALO_LAYERS):
        t_halo[i] = int(_popcount(ref_halos[i] & t_matrix).sum())
        r_halo[i] = int(_popcount(target_halos[i] & r_matrix).sum())
        t_matrix |= ref_halos[i]
        r_matrix |= target_halos[i]
    t_halo[2] = target_pixels - black - t_halo[0] - t_halo[1]
    r_halo[2] = ref_pixels - black - r_halo[0] - r_halo[1]
    white = SIZE * SIZE - target_pixels - ref_pixels + black
    score = (
        OCR_BASE_SCORE
        + OCR_BLACK_SCORE * black
        + OCR_WHITE_SCORE * white
        + sum(t_halo[i] * OCR_TARGET_HALO_SCORES[i] for i in range(3))
        + sum(r_halo[i] * OCR_REFERENCE_HALO_SCORES[i] for i in range(3))
    )
    return score, black


class BitmapClassifier:
    def __init__(self, ref_packed, ref_pixels, ref_halos, labels, top_k: int = 80):
        self.ref_packed = np.asarray(ref_packed, dtype=np.uint64)
        self.ref_pixels = np.asarray(ref_pixels, dtype=np.int64)
        self.ref_halos = [np.asarray(h, dtype=np.uint64) for h in ref_halos]
        self.labels = list(labels)
        self.top_k = top_k
        self.n = len(labels)
        self._translations = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
        self._transforms = valid_transforms()

    def classify(self, glyph: np.ndarray, k: int = 3, alpha: float | None = None) -> tuple[str, float]:
        target = glyph_to_bitmap(glyph)
        target_pixels = int(target.sum())
        if target_pixels == 0:
            return "", 0.0
        target_packed = _pack(target)

        best_basic = np.full(self.n, -1e18, dtype=np.float64)
        for ht, vt in self._translations:
            tb = translate_bitmap(target, ht, vt)
            tp = _pack(tb)
            black = _popcount(tp[None, :] & self.ref_packed).sum(axis=1)
            basic = 4 * SIZE * SIZE - 4 * target_pixels - 4 * self.ref_pixels + 8 * black
            np.maximum(best_basic, basic, out=best_basic)

        k = min(self.top_k, self.n)
        top = np.argpartition(best_basic, -k)[-k:]

        target_halos = build_halo_packed(target)
        best_score = -1e18
        best_idx = int(top[0])
        best_black = 0
        for idx in top:
            idx = int(idx)
            score, black = _refined_score(
                target_packed, target_halos, target_pixels,
                self.ref_packed[idx], [h[idx] for h in self.ref_halos], int(self.ref_pixels[idx]),
            )
            if score > best_score:
                best_score = score
                best_idx = idx
                best_black = black

        char = self.labels[best_idx]
        denom = max(target_pixels, int(self.ref_pixels[best_idx]), 1)
        conf = min(1.0, best_black / denom)
        return char, float(conf)
