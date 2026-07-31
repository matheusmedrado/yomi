"""Amostragem, contraste, filtragem passa-baixa e máscara de cor."""
from __future__ import annotations

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Lab 00 — amostragem
# ---------------------------------------------------------------------------

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Converte imagem BGR (ou já cinza) para uint8 de um canal.

    Aceita entrada colorida (HxWx3) ou em escala de cinza (HxW). O espaço de cor
    é tratado como BGR porque é isso que o `cv2.imread` devolve; a conversão usa
    os pesos de luminância padrão, não só a média dos canais.
    """
    if image.ndim == 2:
        return image
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError(f"Esperava imagem 2D ou 3D com 3/4 canais, recebi shape={image.shape}")
    if image.shape[2] == 4:
        image = image[:, :, :3]
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_longest_edge(image: np.ndarray, target: int) -> np.ndarray:
    """Redimensiona para que o lado maior seja `target` (Lab 01).

    Nunca faz upscale: se a imagem já for menor que `target`, ela é devolvida
    sem alteração. A proporção é preservada.
    """
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= target:
        return image
    scale = target / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# Lab 03 — contraste
# ---------------------------------------------------------------------------

def clahe_equalize(gray: np.ndarray, clip_limit: float = 2.0,
                   tile_grid: tuple[int, int] = (8, 8)) -> np.ndarray:
    """Aplica CLAHE (equalização adaptativa limitada de histograma).

    Melhor que equalização global pra páginas de mangá onde iluminação e
    densidade de tinta variam ao longo da página. A saída mantém o dtype/range original.
    """
    if gray.ndim != 2:
        raise ValueError("CLAHE espera imagem em escala de cinza (HxW).")
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    return clahe.apply(gray)


# ---------------------------------------------------------------------------
# Lab 04 — filtragem passa-baixa
# ---------------------------------------------------------------------------

def denoise(gray: np.ndarray, method: str = "bilateral",
            ksize: int = 3) -> np.ndarray:
    """Aplica filtro de redução de ruído (Lab 04).

    Métodos disponíveis:
      - "gaussian":  rápido, suavização leve, borra bordas.
      - "median":    bom pra artefatos de scan tipo sal-e-pimenta; preserva bordas.
      - "bilateral": preserva bordas; recomendado pra linhas de tinta de mangá.
    """
    if gray.ndim != 2:
        raise ValueError("denoise espera imagem em escala de cinza (HxW).")
    method = method.lower()
    if method == "gaussian":
        return cv2.GaussianBlur(gray, (ksize, ksize), sigmaX=0)
    if method == "median":
        k = max(3, ksize | 1)  # odd
        return cv2.medianBlur(gray, k)
    if method == "bilateral":
        # d=ksize*2 é um valor usual para o diâmetro do filtro.
        return cv2.bilateralFilter(gray, d=max(3, ksize * 2),
                                   sigmaColor=75, sigmaSpace=75)
    raise ValueError(f"metodo de denoise desconhecido: {method!r}")


# ---------------------------------------------------------------------------
# Lab 09 — tratamento de cor: máscara de tinta e papel
# ---------------------------------------------------------------------------

def color_to_text_mask(image: np.ndarray,
                       sat_threshold: int = 60,
                       val_threshold: int = 80) -> np.ndarray:
    """Produz máscara binária com tinta branca sobre fundo preto.

    Estratégia (Lab 09):
      1. Converte BGR → HSV.
      2. Descarta pixels muito saturados (áreas pintadas/coloridas geralmente
         não são texto em mangá).
      3. Descarta pixels muito claros (papel / branco).
      4. O resto é a máscara de tinta.
    """
    if image.ndim == 2:
        # Já está em cinza: preserva os pixels escuros.
        mask = (image < val_threshold).astype(np.uint8) * 255
        return mask
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError(f"Esperava imagem 2D ou 3D, recebi shape={image.shape}")
    if image.shape[2] == 4:
        image = image[:, :, :3]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # Tinta: baixa saturação e baixa intensidade.
    ink = ((sat < sat_threshold) & (val < val_threshold)).astype(np.uint8) * 255
    return ink


# ---------------------------------------------------------------------------
# Nível principal: pré-processamento da página inteira
# ---------------------------------------------------------------------------

def preprocess_page(image: np.ndarray, target_longest: int = 1600,
                    denoise_method: str = "bilateral",
                    apply_clahe: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Executa o pré-processamento completo em uma página de mangá.

    Retorna
    -------
    gray : np.ndarray
        Imagem em escala de cinza redimensionada com o lado maior igual a `target_longest`.
    mask : np.ndarray
        Máscara binária de tinta na escala da imagem **original**. Manter a máscara
        na resolução original facilita mapear as caixas delimitadoras de volta
        pras coordenadas dos pixels sem ter que ficar convertendo.
    """
    if image.ndim not in (2, 3):
        raise ValueError(f"shape invalido para preprocess_page: {image.shape}")
    mask = color_to_text_mask(image)
    gray = to_grayscale(image)
    if apply_clahe:
        gray = clahe_equalize(gray)
    gray = denoise(gray, method=denoise_method)
    gray = resize_longest_edge(gray, target_longest)
    return gray, mask
