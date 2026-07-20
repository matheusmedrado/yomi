"""KANJIDIC2 dictionary loader and lookup.

Downloads the KANJIDIC2 XML (EDRDG, CC BY-SA 4.0) once, parses it into a
compact JSON cache, and provides fast per-kanji lookups with Portuguese
meanings (fallback to English when PT is unavailable).
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, TypedDict
from urllib.request import urlopen

log = logging.getLogger(__name__)

KANJIDIC2_URL = "http://www.edrdg.org/kanjidic/kanjidic2.xml.gz"
CACHE_DIR = Path(os.environ.get("YOMI_CACHE_DIR", Path.home() / ".cache" / "yomi"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
XML_PATH = CACHE_DIR / "kanjidic2.xml.gz"
JSON_PATH = CACHE_DIR / "kanjidic2.json"


class KanjiInfo(TypedDict):
    char: str
    meanings_pt: list[str]
    meanings_en: list[str]
    kun: list[str]
    on: list[str]
    strokes: int
    grade: int
    jlpt: int


_kanji_db: Optional[dict[str, KanjiInfo]] = None


def _download_xml() -> Path:
    if XML_PATH.exists():
        return XML_PATH
    log.info("kanji: downloading KANJIDIC2 from %s ...", KANJIDIC2_URL)
    try:
        with urlopen(KANJIDIC2_URL, timeout=30) as resp:
            data = resp.read()
        XML_PATH.write_bytes(data)
        log.info("kanji: saved %d bytes to %s", len(data), XML_PATH)
    except Exception as e:
        log.warning("kanji: download failed: %s", e)
        raise
    return XML_PATH


def _parse_xml(xml_path: Path) -> dict[str, KanjiInfo]:
    log.info("kanji: parsing %s ...", xml_path)
    db: dict[str, KanjiInfo] = {}
    opener = gzip.open if str(xml_path).endswith(".gz") else open
    with opener(xml_path, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    for char_el in root.findall("character"):
        literal_el = char_el.find("literal")
        if literal_el is None or not literal_el.text:
            continue
        char = literal_el.text
        misc = char_el.find("misc")
        strokes = 0
        grade = 0
        jlpt = 0
        if misc is not None:
            sc = misc.find("stroke_count")
            if sc is not None and sc.text:
                strokes = int(sc.text)
            gr = misc.find("grade")
            if gr is not None and gr.text:
                grade = int(gr.text)
            jl = misc.find("jlpt")
            if jl is not None and jl.text:
                jlpt = int(jl.text)
        rm = char_el.find("reading_meaning")
        rmgroup = rm.find("rmgroup") if rm is not None else None
        kun: list[str] = []
        on: list[str] = []
        meanings_pt: list[str] = []
        meanings_en: list[str] = []
        if rmgroup is not None:
            for r in rmgroup.findall("reading"):
                r_type = r.get("r_type", "")
                if r_type == "ja_kun" and r.text:
                    kun.append(r.text)
                elif r_type == "ja_on" and r.text:
                    on.append(r.text)
            for m in rmgroup.findall("meaning"):
                lang = m.get("m_lang", "")
                if m.text:
                    if lang == "pt":
                        meanings_pt.append(m.text)
                    elif lang == "" or lang == "en":
                        meanings_en.append(m.text)
        db[char] = KanjiInfo(
            char=char,
            meanings_pt=meanings_pt,
            meanings_en=meanings_en,
            kun=kun,
            on=on,
            strokes=strokes,
            grade=grade,
            jlpt=jlpt,
        )
    log.info("kanji: loaded %d entries", len(db))
    return db


def _load_db() -> dict[str, KanjiInfo]:
    global _kanji_db
    if _kanji_db is not None:
        return _kanji_db
    if JSON_PATH.exists():
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                _kanji_db = json.load(f)
            log.info("kanji: loaded %d entries from JSON cache", len(_kanji_db))
            return _kanji_db
        except Exception as e:
            log.warning("kanji: JSON cache corrupt, rebuilding: %s", e)
            JSON_PATH.unlink(missing_ok=True)
    try:
        xml_path = _download_xml()
    except Exception:
        _kanji_db = {}
        return _kanji_db
    _kanji_db = _parse_xml(xml_path)
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(_kanji_db, f, ensure_ascii=False)
    except Exception as e:
        log.warning("kanji: could not write JSON cache: %s", e)
    return _kanji_db


def lookup(chars: list[str]) -> list[KanjiInfo]:
    db = _load_db()
    results: list[KanjiInfo] = []
    seen: set[str] = set()
    for c in chars:
        if c in seen:
            continue
        seen.add(c)
        info = db.get(c)
        if info is not None:
            results.append(info)
    return results
