"""Tradução Japonês → Português via endpoint gratuito do Google Translate.

Usa o endpoint não documentado `translate.googleapis.com` (o mesmo usado
pela extensão de navegador). Grátis, sem chave de API, limites generosos pra
uso pessoal. Em caso de falha retorna string vazia pra UI nunca quebrar —
a linha de tradução simplesmente some.
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

_TRANSLATE_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)

_cache: dict[str, str] = {}
_session: Optional[requests.Session] = None
_TIMEOUT = 6


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Yomi/1.0 (manga reader; PDI UFU)",
        })
    return _session


def to_portuguese(text: str, source: str = "ja") -> str:
    if not text or not text.strip():
        return ""
    key = f"{source}:{text}"
    if key in _cache:
        return _cache[key]
    try:
        url = _TRANSLATE_URL.format(
            sl=source, tl="pt", q=quote(text, safe="")
        )
        resp = _get_session().get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        parts: list[str] = []
        for chunk in data:
            if isinstance(chunk, list):
                for item in chunk:
                    if isinstance(item, list) and item and isinstance(item[0], str):
                        parts.append(item[0])
        translation = "".join(parts).strip()
        _cache[key] = translation
        return translation
    except Exception as e:
        log.warning("translate: failed for %r: %s", text[:60], e)
        _cache[key] = ""
        return ""
