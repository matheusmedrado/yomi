#!/usr/bin/env python3
"""Cria os dois CBZs pareados usados na demonstração de robustez do Yomi."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pipeline.robustness import add_salt_pepper


DEFAULT_PAGES = ("08.png", "09.png", "10.png", "11.png")
FIXED_ZIP_TIME = (2026, 7, 31, 12, 0, 0)


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data, compresslevel=6)


def _encode_png(image, page_name: str) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"não foi possível codificar {page_name}")
    return encoded.tobytes()


def create_pair(source_dir: Path, clean_output: Path, degraded_output: Path,
                pages: tuple[str, ...], density: float) -> None:
    clean_output.parent.mkdir(parents=True, exist_ok=True)
    degraded_output.parent.mkdir(parents=True, exist_ok=True)

    with (
        zipfile.ZipFile(clean_output, "w") as clean_zip,
        zipfile.ZipFile(degraded_output, "w") as degraded_zip,
    ):
        for index, page_name in enumerate(pages):
            source = source_dir / page_name
            image = cv2.imread(str(source), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(source)

            archive_name = f"demo/{index + 1:02d}.png"
            clean_data = _encode_png(image, page_name)
            degraded = add_salt_pepper(
                image,
                density=density,
                seed=20260731 + index,
            )
            _write_entry(clean_zip, archive_name, clean_data)
            _write_entry(
                degraded_zip,
                archive_name,
                _encode_png(degraded, page_name),
            )

        manifest_base = (
            "Yomi - amostra controlada para demonstracao PDI\n"
            f"Paginas de origem: {', '.join(pages)}\n"
            "Degradacao: ruido sal-e-pimenta\n"
            f"Densidade: {density:.2f}\n"
            "Seeds deterministicas: 20260731 + indice da pagina\n"
            "Restauracao no app: filtro da mediana 3x3\n"
        )
        _write_entry(
            clean_zip,
            "MANIFESTO.txt",
            ("Variante: limpa, sem alteracao\n" + manifest_base).encode("utf-8"),
        )
        _write_entry(
            degraded_zip,
            "MANIFESTO.txt",
            ("Variante: degradada\n" + manifest_base).encode("utf-8"),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "sample")
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=ROOT / "demo_sample_limpo.cbz",
    )
    parser.add_argument(
        "--degraded-output",
        type=Path,
        default=ROOT / "demo_sample_degradado.cbz",
    )
    parser.add_argument("--density", type=float, default=0.10)
    parser.add_argument("--pages", nargs="+", default=list(DEFAULT_PAGES))
    args = parser.parse_args()

    if not 0 < args.density < 1:
        parser.error("--density deve estar entre 0 e 1")

    create_pair(
        args.source_dir,
        args.clean_output,
        args.degraded_output,
        tuple(args.pages),
        args.density,
    )
    print(f"Limpo:     {args.clean_output}")
    print(f"Degradado: {args.degraded_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
