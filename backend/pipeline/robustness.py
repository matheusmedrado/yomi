"""Degradações controladas e restaurações clássicas para o experimento PDI.

A degradação é aplicada somente depois da localização. Assim, todas as
comparações usam exatamente a mesma caixa e medem apenas o efeito que a
qualidade dos pixels tem sobre o OCR.
"""
from __future__ import annotations

from typing import Literal

import cv2
import numpy as np

from .preprocess import to_grayscale


Degradation = Literal["low_contrast", "gaussian_noise", "salt_pepper"]
DEGRADATIONS: tuple[Degradation, ...] = (
    "low_contrast",
    "gaussian_noise",
    "salt_pepper",
)

LABELS = {
    "low_contrast": "Baixo contraste",
    "gaussian_noise": "Ruído gaussiano",
    "salt_pepper": "Ruído sal-e-pimenta",
}


def _as_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def reduce_contrast(image: np.ndarray, factor: float = 0.05) -> np.ndarray:
    """Comprime a faixa dinâmica ao redor da intensidade média (Lab 03)."""
    if not 0 < factor < 1:
        raise ValueError("factor must be between 0 and 1")
    gray = to_grayscale(image).astype(np.float32)
    center = float(gray.mean())
    degraded = center + factor * (gray - center)
    return _as_bgr(np.clip(degraded, 0, 255).astype(np.uint8))


def add_gaussian_noise(image: np.ndarray, sigma: float = 80.0,
                       seed: int = 0) -> np.ndarray:
    """Adiciona ruído gaussiano aditivo determinístico (Lab 04)."""
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    gray = to_grayscale(image).astype(np.float32)
    rng = np.random.default_rng(seed)
    noisy = gray + rng.normal(0.0, sigma, gray.shape)
    return _as_bgr(np.clip(noisy, 0, 255).astype(np.uint8))


def add_salt_pepper(image: np.ndarray, density: float = 0.10,
                    seed: int = 0) -> np.ndarray:
    """Substitui uma fração dos pixels por preto ou branco (Lab 04)."""
    if not 0 < density < 1:
        raise ValueError("density must be between 0 and 1")
    gray = to_grayscale(image).copy()
    rng = np.random.default_rng(seed)
    draw = rng.random(gray.shape)
    half = density / 2.0
    gray[draw < half] = 0
    gray[(draw >= half) & (draw < density)] = 255
    return _as_bgr(gray)


def degrade(image: np.ndarray, kind: Degradation, seed: int = 0) -> np.ndarray:
    """Aplica uma das degradações padronizadas do experimento."""
    if kind == "low_contrast":
        return reduce_contrast(image)
    if kind == "gaussian_noise":
        return add_gaussian_noise(image, seed=seed)
    if kind == "salt_pepper":
        return add_salt_pepper(image, seed=seed)
    raise ValueError(f"unknown degradation: {kind!r}")


def restore(image: np.ndarray, kind: Degradation) -> np.ndarray:
    """Aplica a técnica clássica adequada à degradação conhecida.

    - baixo contraste: equalização global de histograma (Lab 03);
    - ruído gaussiano: filtro Gaussiano 3x3 (Lab 04);
    - sal-e-pimenta: filtro de mediana 3x3 (Lab 04).
    """
    gray = to_grayscale(image)
    if kind == "low_contrast":
        return _as_bgr(cv2.equalizeHist(gray))
    if kind == "gaussian_noise":
        return _as_bgr(cv2.GaussianBlur(gray, (3, 3), sigmaX=0.9))
    if kind == "salt_pepper":
        return _as_bgr(cv2.medianBlur(gray, 3))
    raise ValueError(f"unknown degradation: {kind!r}")


def degradation_triplet(image: np.ndarray, kind: Degradation,
                        seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retorna original, degradada e restaurada para inspeção lado a lado."""
    degraded = degrade(image, kind, seed=seed)
    return image, degraded, restore(degraded, kind)
