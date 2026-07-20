from __future__ import annotations

from unittest.mock import patch, MagicMock
from translate import to_portuguese, _cache


def test_to_portuguese_empty():
    assert to_portuguese("") == ""
    assert to_portuguese("   ") == ""


def test_to_portuguese_cached():
    _cache.clear()
    _cache["ja:テスト"] = "teste"
    result = to_portuguese("テスト")
    assert result == "teste"


def test_to_portuguese_success():
    _cache.clear()
    mock_response = MagicMock()
    mock_response.json.return_value = [[["teste", "テスト", None, None, None]]]
    mock_response.raise_for_status = MagicMock()

    with patch("translate._get_session") as mock_session:
        mock_session.return_value.get.return_value = mock_response
        result = to_portuguese("テスト")
        assert result == "teste"


def test_to_portuguese_failure():
    _cache.clear()
    with patch("translate._get_session") as mock_session:
        mock_session.return_value.get.side_effect = Exception("network error")
        result = to_portuguese("テスト")
        assert result == ""
