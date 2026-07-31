"""Etapa de detecção de bordas (Lab 05).

Fornece os três operadores clássicos de borda que aparecem na disciplina:
Sobel (magnitude do gradiente), Laplaciano (derivada de segunda ordem) e Canny
(gradiente + supressão de não-máximos + histerese). Todos retornam imagens
uint8 com o mesmo formato da entrada.
"""
from __future__ import annotations

import cv2
import numpy as np


def sobel(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Magnitude do gradiente Sobel, normalizada para uint8."""
    if gray.ndim != 2:
        raise ValueError("sobel espera imagem em escala de cinza (HxW).")
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=ksize)
    mag = cv2.magnitude(gx, gy)
    mag = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return mag.astype(np.uint8)


def laplacian(gray: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Bordas por Laplaciano (segunda ordem), normalizadas para uint8."""
    if gray.ndim != 2:
        raise ValueError("laplacian espera imagem em escala de cinza (HxW).")
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=ksize)
    lap = cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX)
    return lap.astype(np.uint8)


def canny(gray: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    """Bordas de Canny. A saída é binária (somente 0 e 255)."""
    if gray.ndim != 2:
        raise ValueError("canny espera imagem em escala de cinza (HxW).")
    return cv2.Canny(gray, low, high)
