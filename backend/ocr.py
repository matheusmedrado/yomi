"""Wrapper do manga-ocr.

O modelo é carregado **sob demanda no primeiro uso** pra que o resto do app
fique responsivo mesmo se o primeiro hover vier a frio. Mantemos o pipeline
de entrada simples: um crop BGR apertado → BGR→RGB → PIL → modelo.
Uma borda pequena ao redor do crop ajuda o reconhecedor com as beiradas do balão.

Se o `manga-ocr` não estiver instalado (ex.: durante a parte do desenvolvimento
em que só queremos o pipeline clássico rodando), `MangaOcrService.recognize`
devolve string vazia e loga uma vez. É isso que permite o resto do projeto
funcionar sem a dependência pesada de DL.
"""
from __future__ import annotations

import io
import logging
import os
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

_LOCAL_MODEL = Path(__file__).resolve().parent.parent / "local" / "manga-ocr-base"
DEFAULT_MODEL_SOURCE = os.environ.get(
    "MANGA_OCR_MODEL",
    str(_LOCAL_MODEL) if _LOCAL_MODEL.is_dir() else "kha-white/manga-ocr-base",
)


class MangaOcrService:
    """Singleton preguiçoso do `MangaOcr`."""

    _instance: Optional["MangaOcrService"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._mocr = None
        self._tried_load = False
        self._available: bool | None = None
        # Serializa a inferência — chamadas concorrentes PyTorch/MPS do servidor
        # com threads do Flask podem crashar ou corromper os resultados.
        self._infer_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "MangaOcrService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- API pública -----------------------------------------------------

    def warm_up(self) -> bool:
        """Carrega o modelo de forma adiantada. Retorna True se carregou com sucesso."""
        self._ensure_loaded()
        return self._available is True

    def is_available(self) -> bool:
        if self._available is None:
            self._ensure_loaded()
        return self._available is True

    def recognize(self, crop_bgr: np.ndarray, padding: int = 12) -> str:
        """Reconhece o texto em japonês num crop apertado de um balão de fala.

        `crop_bgr` é uma imagem BGR no padrão do OpenCV. Uma borda branca pequena
        é adicionada pra o modelo não ver tinta encostando nas beiradas.
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return ""
        self._ensure_loaded()
        if not self.is_available():
            return ""

        pad = max(0, int(padding))
        if pad > 0:
            crop_bgr = cv2.copyMakeBorder(
                crop_bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT,
                value=(255, 255, 255),
            )
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        import time
        t0 = time.perf_counter()
        try:
            with self._infer_lock:
                text = self._mocr(pil)  # type: ignore[misc]
        except Exception as e:  # noqa: BLE001
            log.exception("manga-ocr recognize failed: %s", e)
            return ""
        dt = (time.perf_counter() - t0) * 1000
        log.info("ocr: %.0fms crop=%dx%d text=%r",
                 dt, crop_bgr.shape[1], crop_bgr.shape[0], (text or "")[:60])
        return (text or "").strip()

    # ---- internos --------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._available is not None:
            return
        with self._lock:
            if self._available is not None:
                return
            self._tried_load = True
            try:
                from manga_ocr import MangaOcr  # type: ignore
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "manga-ocr not installed (%s); OCR will return empty strings.",
                    e,
                )
                self._available = False
                return
            try:
                # Uma pasta de modelo local permite que OCR e benchmark CER
                # funcionem offline depois do download único do Hugging Face.
                self._mocr = MangaOcr(pretrained_model_name_or_path=DEFAULT_MODEL_SOURCE)
                self._available = True
                log.info("manga-ocr carregado com sucesso.")
            except Exception as e:  # noqa: BLE001
                log.exception("Failed to initialize manga-ocr: %s", e)
                self._available = False


def encode_crop_for_debug(crop_bgr: np.ndarray) -> bytes:
    """Encode a crop as PNG bytes for the debug endpoints."""
    ok, buf = cv2.imencode(".png", crop_bgr)
    if not ok:
        return b""
    return buf.tobytes()
