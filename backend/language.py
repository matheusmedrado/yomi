"""Language layer: rule-based kana/kanji -> furigana/romaji conversion + analysis.

`pykakasi` is a port of the classical `kakasi` system — a rules-based
converter, not a language model. That fits the project's "no AI" policy
nicely: it is a deterministic lookup table, not deep learning.

The output is a small dict so the frontend can render both readings in the
hover overlay without further processing.
"""
from __future__ import annotations

from typing import TypedDict

import pykakasi


class Reading(TypedDict):
    text: str
    furigana: str
    romaji: str


class Token(TypedDict):
    surface: str
    furigana: str
    romaji: str
    script: str


class Analysis(TypedDict):
    tokens: list[Token]
    kanji_chars: list[str]


_kks = pykakasi.kakasi()

_HIRA_RANGES = [(0x3040, 0x309F)]
_KATA_RANGES = [(0x30A0, 0x30FF), (0xFF66, 0xFF9D)]
_KANJI_RANGES = [(0x4E00, 0x9FFF)]
_KANA_EXTRAS = {0x30FC, 0x3005, 0x3006, 0x30F6, 0x30F5, 0x309F, 0x30FF}


def _char_script(c: str) -> str:
    cp = ord(c)
    if cp in _KANA_EXTRAS:
        if cp == 0x3005:
            return "kanji"
        if cp == 0x30FC:
            return "katakana"
        return "hiragana"
    for lo, hi in _HIRA_RANGES:
        if lo <= cp <= hi:
            return "hiragana"
    for lo, hi in _KATA_RANGES:
        if lo <= cp <= hi:
            return "katakana"
    for lo, hi in _KANJI_RANGES:
        if lo <= cp <= hi:
            return "kanji"
    return "other"


def _word_script(word: str) -> str:
    scripts = {_char_script(c) for c in word if _char_script(c) != "other"}
    if "kanji" in scripts:
        return "kanji"
    if "katakana" in scripts and "hiragana" not in scripts:
        return "katakana"
    if "hiragana" in scripts and "katakana" not in scripts:
        return "hiragana"
    if "katakana" in scripts and "hiragana" in scripts:
        return "katakana"
    return "other"


def to_reading(text: str) -> Reading:
    if not text:
        return {"text": "", "furigana": "", "romaji": ""}
    result = _kks.convert(text)
    furigana = "".join(item.get("hira", "") or item.get("orig", "") for item in result)
    romaji = "".join(item.get("hepburn", "") or item.get("kunrei", "")
                     or item.get("orig", "") for item in result)
    return {"text": text, "furigana": furigana, "romaji": romaji}


def analyze(text: str) -> Analysis:
    if not text:
        return {"tokens": [], "kanji_chars": []}
    result = _kks.convert(text)
    tokens: list[Token] = []
    kanji_set: list[str] = []
    seen: set[str] = set()
    for item in result:
        surface = item.get("orig", "")
        if not surface:
            continue
        hira = item.get("hira", "") or surface
        hepburn = item.get("hepburn", "") or item.get("kunrei", "") or surface
        script = _word_script(surface)
        tokens.append(Token(
            surface=surface,
            furigana=hira,
            romaji=hepburn,
            script=script,
        ))
        for c in surface:
            if _char_script(c) == "kanji" and c not in seen:
                seen.add(c)
                kanji_set.append(c)
    return {"tokens": tokens, "kanji_chars": kanji_set}
