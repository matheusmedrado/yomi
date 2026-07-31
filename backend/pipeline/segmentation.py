"""Funções auxiliares de limiarização, morfologia, CCs e watershed."""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TextRegion:
    """Caixa na imagem original, no formato (x, y, w, h)."""
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


# Contador do módulo para gerar IDs únicos a cada detecção.
_id_counter = 0


def _next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter


# ---------------------------------------------------------------------------
# Lab 06 — limiar de Otsu
# ---------------------------------------------------------------------------

def otsu_threshold(gray_or_mask: np.ndarray,
                   invert: bool | None = None) -> np.ndarray:
    """Limiar automático de Otsu em imagem cinza ou máscara binária.

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
        # Convenção: tinta (texto) é branca na máscara. Inverte se necessário.
        frac_white = float(np.count_nonzero(binary)) / binary.size
        if frac_white > 0.5:
            binary = cv2.bitwise_not(binary)
    elif invert:
        binary = cv2.bitwise_not(binary)
    return binary


# ---------------------------------------------------------------------------
# Lab 07 — morfologia
# ---------------------------------------------------------------------------

def morphology_cleanup(binary: np.ndarray,
                       open_k: int = 3,
                       close_k: int = 5) -> np.ndarray:
    """Limpa uma máscara binária com abertura e fechamento (Lab 07).

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
# Lab 02 — componentes conectados
# ---------------------------------------------------------------------------

def connected_components(binary: np.ndarray, min_area: int = 30,
                         max_area: int | None = None,
                         min_aspect: float = 0.05,
                         max_aspect: float = 20.0) -> list[TextRegion]:
    """Rotula componentes conectados e retorna os aprovados como TextRegion.

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
# Lab 08 — watershed para texto encostado
# ---------------------------------------------------------------------------

def _looks_like_text_blob(region: TextRegion, binary: np.ndarray,
                          min_fill: float = 0.15,
                          max_fill: float = 0.85) -> bool:
    """Heurística para identificar um componente denso, candidato a watershed."""
    x, y, w, h = region.x, region.y, region.w, region.h
    crop = binary[y:y + h, x:x + w]
    if crop.size == 0:
        return False
    fill = float(np.count_nonzero(crop)) / crop.size
    return min_fill < fill < max_fill


def watershed_split(binary: np.ndarray, region: TextRegion) -> list[TextRegion]:
    """Aplica transformada de distância e watershed em um componente (Lab 08).

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
        # Limita à caixa original para descartar bordas marcadas com -1.
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
# Detecção de balões de fala (Labs 02, 06 e 07)
# ---------------------------------------------------------------------------

def _enclosed_uniform_regions(gray: np.ndarray, bright: bool,
                              thresh: int,
                              min_area_frac: float,
                              max_area_frac: float,
                              min_extent: float,
                              min_solidity: float,
                              min_interior_frac: float,
                              ) -> list[TextRegion]:
    """Encontra regiões fechadas de cor uniforme, interiores dos balões.

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
    # Fecha pequenas falhas no contorno do balão e nas caudas.
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
        # Uniformidade interna: fração da caixa dominada pela cor do balão.
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
    """Detecta balões brancos e pretos, com texto invertido, em uma página.

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
    # Ordem aproximada de mangá: cima para baixo e direita para esquerda.
    out.sort(key=lambda r: (r.y, -r.x))
    return out


# ---------------------------------------------------------------------------
# Agrupamento de componentes em linhas de texto (ou colunas verticais)
# ---------------------------------------------------------------------------

def cluster_lines(regions: list[TextRegion], gap_factor: float = 0.7,
                  vertical: bool = False) -> list[list[TextRegion]]:
    """Agrupamento guloso de componentes em linhas.

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
        # Agrupa pela sobreposição em x e ordena por y.
        def key(r: TextRegion) -> tuple[int, int]:
            return (r.x, r.y)
        primary_axis = lambda r: (r.x, r.x + r.w)
        secondary_axis = lambda r: (r.y, r.y + r.h)
    else:
        # Agrupa pela sobreposição em y e ordena por x.
        def key(r: TextRegion) -> tuple[int, int]:
            return (r.y, r.x)
        primary_axis = lambda r: (r.y, r.y + r.h)
        secondary_axis = lambda r: (r.x, r.x + r.w)

    # Ordena pelo eixo principal e depois pelo secundário.
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

    # Ordena cada linha na direção de leitura.
    for line in lines:
        if vertical:
            line.sort(key=lambda r: r.y)
        else:
            line.sort(key=lambda r: r.x)
    return lines


# ---------------------------------------------------------------------------
# Nível principal: da página às regiões de texto
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
    """Extrai regiões candidatas de uma imagem cinza ou máscara."""
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
        # Remove linhas longas com abertura morfológica: contornos de balões,
        # quadros, divisórias e linhas de velocidade.
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
        # Expande a máscara de linhas para remover também suas bordas suaves.
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

    # Ordem aproximada: cima para baixo e direita para esquerda.
    kept.sort(key=lambda r: (r.y, -r.x if vertical else r.x))
    return kept
