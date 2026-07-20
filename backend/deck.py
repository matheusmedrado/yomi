"""Anki .apkg deck builder using genanki.

Builds a deck from a list of study cards, packaging the bubble crop images
as media files inside the .apkg archive.
"""
from __future__ import annotations

import hashlib
import io
import logging
import time
from typing import TypedDict

import genanki

log = logging.getLogger(__name__)

MODEL_ID = 1749641989
DECK_ID = 1749641990

MODEL = genanki.Model(
    MODEL_ID,
    "Yomi — Manga Reader",
    fields=[
        {"name": "Imagem"},
        {"name": "Frase"},
        {"name": "Furigana"},
        {"name": "Romaji"},
        {"name": "Tradução"},
        {"name": "Kanji"},
    ],
    templates=[
        {
            "name": "Yomi Card",
            "qfmt": """
<div style="text-align: center; font-family: 'Noto Serif JP', serif;">
  {{Imagem}}
  <div style="margin-top: 12px; font-size: 22px;">{{Frase}}</div>
</div>
""".strip(),
            "afmt": """
<div style="text-align: center; font-family: 'Noto Serif JP', serif;">
  {{Imagem}}
  <div style="margin-top: 12px; font-size: 22px;">{{Frase}}</div>
  <div style="margin-top: 8px; font-size: 16px; color: #5b5b5b;">{{Furigana}}</div>
  <div style="margin-top: 4px; font-size: 13px; color: #888; font-family: monospace;">{{Romaji}}</div>
  <hr style="margin: 16px auto; width: 60%;">
  <div style="font-size: 18px; color: #c8102e;">{{Tradução}}</div>
  <div style="margin-top: 12px; font-size: 13px; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto;">{{Kanji}}</div>
</div>
""".strip(),
        },
    ],
    css="""
.card { font-family: 'Noto Serif JP', serif; font-size: 20px; text-align: center; color: #0a0a0a; background: #fafaf7; padding: 20px; }
""",
)


class CardPayload(TypedDict):
    page: int
    region_id: int
    text: str
    furigana: str
    romaji: str
    translation: str
    kanji_notes: str
    image_filename: str
    image_bytes: bytes


def _guid(text: str, page: int, region_id: int) -> int:
    raw = f"{text}:{page}:{region_id}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:16], 16)


def build_apkg(cards: list[CardPayload]) -> bytes:
    deck = genanki.Deck(DECK_ID, "Yomi — Manga Reader")
    media: list[tuple[str, bytes]] = []
    for c in cards:
        note = genanki.Note(
            model=MODEL,
            fields=[
                f'<img src="{c["image_filename"]}" style="max-width:300px;">',
                c["text"],
                c["furigana"],
                c["romaji"],
                c["translation"],
                c["kanji_notes"],
            ],
            guid=genanki.guid_for(_guid(c["text"], c["page"], c["region_id"])),
        )
        deck.add_note(note)
        media.append((c["image_filename"], c["image_bytes"]))
    pkg = genanki.Package(deck)
    pkg.media_files = []
    buf = io.BytesIO()
    pkg.write_to_file(buf)
    result = buf.getvalue()
    log.info("deck: built .apkg with %d cards, %d bytes", len(cards), len(result))
    return result
