"""CBZ/zip extraction.

A manga CBZ is just a zip archive of page images, sorted in the natural
reading order (page-001, page-002, ...). We accept .cbz and .zip uploads,
sort entries by their natural name, and write them as individual files
inside a per-session directory.
"""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _natural_key(name: str) -> list:
    """Sort key that understands `page_2 < page_10` instead of `page_10 < page_2`."""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


@dataclass
class ExtractedVolume:
    session_id: str
    pages_dir: Path
    page_files: list[Path]
    title: str | None


def _safe_session_id(raw: str) -> str:
    # hex / uuid-ish only; cap length
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", raw)[:48]
    return cleaned or "session"


def extract_cbz(zip_bytes: bytes, session_id: str,
                 sessions_root: Path) -> ExtractedVolume:
    """Extract a CBZ/zip from raw bytes into a per-session directory.

    The function is intentionally permissive: it skips non-image entries,
    folders, and hidden files. Order is natural by filename.
    """
    session_id = _safe_session_id(session_id)
    pages_dir = sessions_root / session_id
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)

    page_files: list[Path] = []
    # Write through a temp file because zipfile needs a seekable stream.
    tmp_path = pages_dir / "_upload.tmp"
    tmp_path.write_bytes(zip_bytes)

    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            for name in sorted(zf.namelist(), key=_natural_key):
                if name.endswith("/"):
                    continue
                base = os.path.basename(name)
                ext = os.path.splitext(base)[1].lower()
                if ext not in IMAGE_EXTS:
                    continue
                if base.startswith("."):
                    continue
                out = pages_dir / base
                with zf.open(name) as src, out.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                page_files.append(out)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

    return ExtractedVolume(
        session_id=session_id,
        pages_dir=pages_dir,
        page_files=page_files,
        title=None,
    )


def list_pages(pages_dir: Path) -> list[Path]:
    """Return image files in a pages dir sorted in natural order."""
    if not pages_dir.is_dir():
        return []
    files: Iterable[Path] = (
        p for p in pages_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    return sorted(files, key=lambda p: _natural_key(p.name))
