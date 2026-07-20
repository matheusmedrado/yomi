from __future__ import annotations

from language import analyze, _char_script, _word_script


def test_char_script_hiragana():
    assert _char_script("あ") == "hiragana"
    assert _char_script("ん") == "hiragana"


def test_char_script_katakana():
    assert _char_script("ア") == "katakana"
    assert _char_script("ン") == "katakana"


def test_char_script_kanji():
    assert _char_script("日") == "kanji"
    assert _char_script("本") == "kanji"
    assert _char_script("語") == "kanji"


def test_char_script_other():
    assert _char_script("a") == "other"
    assert _char_script("1") == "other"


def test_word_script_kanji():
    assert _word_script("日本語") == "kanji"
    assert _word_script("食べる") == "kanji"


def test_word_script_hiragana():
    assert _word_script("です") == "hiragana"
    assert _word_script("ます") == "hiragana"


def test_word_script_katakana():
    assert _word_script("カタカナ") == "katakana"
    assert _word_script("コンピュータ") == "katakana"


def test_analyze_basic():
    result = analyze("日本語を読む")
    assert len(result["tokens"]) > 0
    assert len(result["kanji_chars"]) > 0
    assert "日" in result["kanji_chars"]
    assert "本" in result["kanji_chars"]
    assert "語" in result["kanji_chars"]
    assert "読" in result["kanji_chars"]


def test_analyze_empty():
    result = analyze("")
    assert result["tokens"] == []
    assert result["kanji_chars"] == []


def test_analyze_tokens_have_scripts():
    result = analyze("猫です")
    for token in result["tokens"]:
        assert "surface" in token
        assert "furigana" in token
        assert "romaji" in token
        assert "script" in token
        assert token["script"] in ("hiragana", "katakana", "kanji", "other")


def test_analyze_katakana_word():
    result = analyze("コンピュータ")
    assert len(result["tokens"]) > 0
    assert result["tokens"][0]["script"] == "katakana"
    assert result["kanji_chars"] == []
