#!/usr/bin/env python3
"""Verifica se o computador está pronto para a apresentação do Yomi."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def mark(ok: bool, message: str) -> bool:
    print(f"[{'OK' if ok else 'FALTA'}] {message}")
    return ok


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--load-models",
        action="store_true",
        help="carrega detector e OCR para validar os pesos (pode demorar)",
    )
    args = parser.parse_args()

    required_ok = True
    recommended_ok = True

    required_ok &= mark(
        sys.version_info[:2] == (3, 11),
        f"Python 3.11 (atual: {sys.version.split()[0]})",
    )
    required_ok &= mark(
        Path(sys.prefix).resolve() == (ROOT / ".venv").resolve(),
        f"ambiente virtual do projeto ativo ({sys.executable})",
    )

    for module in (
        "flask", "cv2", "numpy", "PIL", "torch", "torchvision",
        "manga_ocr", "shapely", "pyclipper", "wandb", "jupyterlab",
    ):
        required_ok &= mark(module_available(module), f"módulo Python: {module}")

    detector_code = ROOT / "backend" / "comic_text_detector" / "inference.py"
    detector_model = ROOT / "local" / "comictextdetector.pt"
    detector_cache = Path.home() / ".cache" / "manga-ocr" / "comictextdetector.pt"
    ocr_model = ROOT / "local" / "manga-ocr-base" / "pytorch_model.bin"

    required_ok &= mark(detector_code.is_file(), "código incorporado do detector")
    required_ok &= mark(
        detector_model.is_file() or detector_cache.is_file(),
        "peso comictextdetector.pt (local/ ou cache do usuário)",
    )
    required_ok &= mark(ocr_model.is_file(), "modelo OCR offline em local/manga-ocr-base")
    required_ok &= mark(shutil.which("node") is not None, "Node.js disponível")
    required_ok &= mark(shutil.which("npm") is not None, "npm disponível")
    required_ok &= mark(
        (ROOT / "frontend" / "node_modules").is_dir(),
        "dependências do frontend instaladas (npm ci)",
    )

    for path, label in (
        (ROOT / "demo_sample_limpo.cbz", "CBZ limpo da demonstração"),
        (ROOT / "demo_sample_degradado.cbz", "CBZ degradado da demonstração"),
        (ROOT / "presentation_artifacts" / "robustness" / "results.json",
         "resultados auditados do notebook"),
        (ROOT / "presentation_artifacts" / "robustness" / "evidence_salt_pepper.png",
         "painéis visuais da apresentação"),
    ):
        recommended_ok &= mark(path.is_file(), label)

    if args.load_models and required_ok:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        try:
            from backend.pipeline.detection import get_detector

            detector = get_detector(device="cpu")
            required_ok &= mark(detector.available, "detector encontra o peso")
            if detector.available:
                detector._ensure()  # valida compatibilidade do checkpoint
                mark(True, "checkpoint do detector carregado")
        except Exception as exc:  # noqa: BLE001
            required_ok = False
            mark(False, f"falha ao carregar detector: {exc}")
        try:
            from backend.ocr import MangaOcrService

            required_ok &= mark(
                MangaOcrService.instance().warm_up(),
                "modelo manga-ocr carregado",
            )
        except Exception as exc:  # noqa: BLE001
            required_ok = False
            mark(False, f"falha ao carregar OCR: {exc}")

    print()
    if required_ok and recommended_ok:
        print("COMPUTADOR PRONTO PARA A APRESENTAÇÃO.")
        return 0
    if required_ok:
        print("Aplicação pronta; faltam apenas artefatos recomendados da apresentação.")
        return 0
    print("Setup incompleto. Consulte docs/SETUP_APRESENTACAO.md.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
