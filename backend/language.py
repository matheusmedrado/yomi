"""Language layer: rule-based kana/kanji -> furigana/romaji conversion.

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


_kks = pykakasi.kakasi()


def to_reading(text: str) -> Reading:
    """Convert a Japanese string into its furigana + romaji reading.

    Returns a dict with the original `text` plus the `furigana` (hiragana)
    and `romaji` (Hepburn) forms. Empty input gives empty strings.

    pykakasi caches internally, so calling `to_reading` repeatedly is cheap.
    """
    if not text:
        return {"text": "", "furigana": "", "romaji": ""}
    result = _kks.convert(text)
    furigana = "".join(item.get("hira", "") or item.get("orig", "") for item in result)
    romaji = "".join(item.get("hepburn", "") or item.get("kunrei", "")
                     or item.get("orig", "") for item in result)
    return {"text": text, "furigana": furigana, "romaji": romaji}
