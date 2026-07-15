from __future__ import annotations

from language import to_reading


def test_to_reading_furigana():
    out = to_reading("日本語")
    assert out["furigana"] == "にほんご"


def test_to_reading_romaji():
    out = to_reading("読み方")
    assert "yomikata" in out["romaji"]


def test_to_reading_empty():
    out = to_reading("")
    assert out["furigana"] == "" and out["romaji"] == ""
