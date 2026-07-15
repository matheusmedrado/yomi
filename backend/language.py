from __future__ import annotations

import pykakasi


class ReadingConverter:
    def __init__(self) -> None:
        self._kakasi = pykakasi.kakasi()

    def convert(self, text: str) -> dict:
        if not text:
            return {"furigana": "", "romaji": "", "tokens": []}
        tokens = []
        furigana_parts = []
        romaji_parts = []
        for item in self._kakasi.convert(text):
            tokens.append(
                {
                    "orig": item["orig"],
                    "hira": item["hira"],
                    "romaji": item["hepburn"],
                }
            )
            furigana_parts.append(item["hira"])
            romaji_parts.append(item["hepburn"])
        return {
            "furigana": "".join(furigana_parts),
            "romaji": " ".join(romaji_parts),
            "tokens": tokens,
        }


def to_reading(text: str) -> dict:
    return ReadingConverter().convert(text)
