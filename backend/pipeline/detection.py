"""Localização de texto e preparação de recortes."""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from .conditioning import ConditioningResult, condition_crop, raw_fallback
from .pdi_localization import localize_page, localize_roi

log = logging.getLogger(__name__)

# comic-text-detector é uma dependência pesada de aprendizado profundo;
# a importação tardia evita exigir o torch no restante do backend.
try:  # pragma: no cover - import guard
    import sys
    # O detector incorporado usa importações absolutas antigas e de pacote;
    # por isso o diretório pai e o próprio diretório precisam estar no caminho.
    _ctd_root = Path(__file__).resolve().parent.parent
    for _ctd_path in (str(_ctd_root), str(_ctd_root / "comic_text_detector")):
        if _ctd_path not in sys.path:
            sys.path.insert(0, _ctd_path)
    from comic_text_detector.inference import TextDetector
    from comic_text_detector.utils.textmask import (
        REFINEMASK_INPAINT,
        refine_mask,
    )
    _HAS_DETECTOR = True
except Exception:  # pragma: no cover
    TextDetector = None  # type: ignore
    REFINEMASK_INPAINT = 0  # type: ignore
    refine_mask = None  # type: ignore
    _HAS_DETECTOR = False


DEFAULT_MODEL = os.environ.get(
    "COMIC_TEXT_DETECTOR_MODEL",
    str(Path.home() / ".cache" / "manga-ocr" / "comictextdetector.pt"),
)

TEXT_HEIGHT = 64
MAX_RATIO_VERT = 16
MAX_RATIO_HOR = 8
ANCHOR_WINDOW = 2
DETECTION_MODES = ("baseline", "hybrid", "pdi_only")
DEFAULT_DETECTION_MODE = os.environ.get("YOMI_DETECTION_MODE", "hybrid")
HYBRID_RELOCALIZE_LINES = os.environ.get("YOMI_HYBRID_RELOCALIZE_LINES", "0") == "1"


@dataclass
class DetectedBlock:
    """Bloco de texto detectado nas coordenadas da imagem original."""
    id: int
    x: int
    y: int
    w: int
    h: int
    vertical: bool
    font_size: int
    crops: List[np.ndarray] = None  # type: ignore
    conditioning: List[ConditioningResult] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.crops is None:
            self.crops = []
        if self.conditioning is None:
            self.conditioning = []

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
            "vertical": bool(self.vertical),
        }


class _Detector:
    """Adaptador singleton simples para o TextDetector."""

    def __init__(self, model_path: str = DEFAULT_MODEL, device: str = "cpu") -> None:
        if not _HAS_DETECTOR:
            raise RuntimeError(
                "comic-text-detector is not installed; detection unavailable."
            )
        self.model_path = model_path
        self.device = device
        self._det: Optional["TextDetector"] = None

    @property
    def available(self) -> bool:
        return _HAS_DETECTOR and Path(self.model_path).is_file()

    def _ensure(self) -> "TextDetector":
        if self._det is None:
            self._det = TextDetector(
                model_path=self.model_path,
                input_size=1024,
                device=self.device,
                act="leaky",
            )
        return self._det

    def detect(self, img: np.ndarray):
        """Executa o detector e retorna ``(mask, mask_refined, blk_list)``."""
        return self._ensure()(img, refine_mode=REFINEMASK_INPAINT,
                              keep_undetected_mask=True)

    def refine(self, img, mask, blk_list):
        if refine_mask is None:
            return mask
        return refine_mask(img, mask, blk_list, refine_mode=REFINEMASK_INPAINT)


_detector_instance: Optional[_Detector] = None


def get_detector(model_path: str = DEFAULT_MODEL, device: str = "cpu") -> _Detector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _Detector(model_path=model_path, device=device)
    return _detector_instance


def _condition_line(block: DetectedBlock, raw: np.ndarray, max_ratio: int,
                    line_idx: int) -> None:
    if raw is None or raw.size == 0:
        return
    try:
        conditioned = condition_crop(raw, max_ratio=max_ratio)
    except Exception as exc:  # unexpected: preserve a traceable raw escape hatch
        log.warning("raw_fallback block=%s line=%s: %s", block.id, line_idx, exc)
        conditioned = raw_fallback(raw)
    block.crops.extend(conditioned.crops)
    block.conditioning.append(conditioned)


def _pdi_only_blocks(img: np.ndarray) -> List[DetectedBlock]:
    blocks: List[DetectedBlock] = []
    for next_id, region in enumerate(localize_page(img)):
        block = DetectedBlock(
            id=next_id, x=region.x, y=region.y, w=region.w, h=region.h,
            vertical=region.vertical, font_size=0,
        )
        for line_idx, line in enumerate(region.lines):
            max_ratio = MAX_RATIO_VERT if line.vertical else MAX_RATIO_HOR
            _condition_line(block, line.raw, max_ratio, line_idx)
        if block.crops:
            blocks.append(block)
    return blocks


def detect_blocks(img: np.ndarray,
                  detector: Optional[_Detector] = None,
                  device: str = "cpu",
                  mode: str | None = None) -> List[DetectedBlock]:
    """Detecta blocos de texto em uma página BGR em resolução original.

    Retorna ``DetectedBlock`` em ordem aproximada de leitura de mangá
    (cima→baixo, direita→esquerda), com recortes prontos para OCR.
    """
    mode = mode or DEFAULT_DETECTION_MODE
    if mode not in DETECTION_MODES:
        raise ValueError(f"unknown detection mode {mode!r}; expected one of {DETECTION_MODES}")
    if mode == "pdi_only":
        return _pdi_only_blocks(img)
    if detector is None:
        detector = get_detector(device=device)
    if not detector.available:
        return []

    _mask, _mask_refined, blk_list = detector.detect(img)

    out: List[DetectedBlock] = []
    next_id = 0
    for blk in blk_list:
        vertical = bool(getattr(blk, "vertical", False))
        font_size = int(getattr(blk, "font_size", 0) or 0)
        x1, y1, x2, y2 = [int(v) for v in blk.xyxy]
        block = DetectedBlock(
            id=next_id, x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1),
            vertical=vertical, font_size=font_size,
        )
        try:
            lines = list(blk.lines_array())
        except Exception:  # pragma: no cover
            lines = []
        if mode == "hybrid" and HYBRID_RELOCALIZE_LINES:
            pdi_region = localize_roi(img, (x1, y1, block.w, block.h), vertical)
            if pdi_region.lines and len(pdi_region.lines) <= len(lines):
                for li, line in enumerate(pdi_region.lines):
                    max_ratio = MAX_RATIO_VERT if line.vertical else MAX_RATIO_HOR
                    _condition_line(block, line.raw, max_ratio, li)
                out.append(block)
                next_id += 1
                continue

        for li in range(len(lines)):
            raw = blk.get_transformed_region(img, li, TEXT_HEIGHT)
            if raw is None or raw.size == 0:
                continue
            horizontal_raw = (
                cv2.rotate(raw, cv2.ROTATE_90_CLOCKWISE) if vertical else raw
            )
            if mode == "baseline":
                block.crops.append(horizontal_raw)
            else:
                max_ratio = MAX_RATIO_VERT if vertical else MAX_RATIO_HOR
                _condition_line(block, horizontal_raw, max_ratio, li)
        out.append(block)
        next_id += 1

    # Ordem aproximada: cima para baixo e direita para esquerda.
    out.sort(key=lambda b: (b.y, -b.x))
    return out
