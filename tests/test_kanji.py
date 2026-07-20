from __future__ import annotations

from kanji import KanjiInfo


def test_kanji_info_structure():
    info = KanjiInfo(
        char="日",
        meanings_pt=["dia", "sol"],
        meanings_en=["day", "sun"],
        kun=["ひ", "ひ.る"],
        on=["ニチ", "ジツ"],
        strokes=4,
        grade=1,
        jlpt=4,
    )
    assert info["char"] == "日"
    assert "dia" in info["meanings_pt"]
    assert "sun" in info["meanings_en"]
    assert "ひ" in info["kun"]
    assert "ニチ" in info["on"]
    assert info["strokes"] == 4
    assert info["grade"] == 1
    assert info["jlpt"] == 4
