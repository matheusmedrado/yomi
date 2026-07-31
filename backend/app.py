"""Yomi — servidor Flask.

Endpoints (tudo em /api/*; o resto serve o build do React quando disponível):
  POST /api/load                  envia um CBZ, devolve session_id + número de páginas
  GET  /api/page/<sid>/<n>       imagem da página (aceita ?w=200 pra thumbnail)
  POST /api/regions               roda o pipeline PDI na página n, retorna caixas
  POST /api/ocr                   roda manga-ocr + leitura + análise em uma região
  GET  /api/region_image/<sid>/<page>/<rid>  crop do balão (JPEG)
  POST /api/deck/export           gera .apkg do Anki com os cards enviados
  GET  /api/debug/<stage>/<sid>/<n>  imagem de estágio intermediário do pipeline
  GET  /api/health                 probe de saúde do servidor
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

# Permite rodar com `python backend/app.py` encontrando os módulos irmãos sem precisar de um pacote.
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backend import cbz  # type: ignore
    from backend.language import to_reading, analyze  # type: ignore
    from backend.ocr import MangaOcrService  # type: ignore
    from backend.pipeline import debug as pipeline_debug  # type: ignore
    from backend.pipeline import preprocess, segmentation  # type: ignore
    from backend.pipeline.detection import (  # type: ignore
        DEFAULT_DETECTION_MODE, DETECTION_MODES, detect_blocks, get_detector,
    )
    from backend.kanji import lookup as kanji_lookup  # type: ignore
    from backend.translate import to_portuguese  # type: ignore
    from backend.deck import build_apkg, CardPayload  # type: ignore
else:
    from . import cbz
    from .language import to_reading, analyze
    from .ocr import MangaOcrService
    from .pipeline import debug as pipeline_debug
    from .pipeline import preprocess, segmentation
    from .pipeline.detection import (
        DEFAULT_DETECTION_MODE, DETECTION_MODES, detect_blocks, get_detector,
    )
    from .kanji import lookup as kanji_lookup
    from .translate import to_portuguese
    from .deck import build_apkg, CardPayload

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
REPO_DIR = BACKEND_DIR.parent
SESSIONS_DIR = BACKEND_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_DIST = REPO_DIR / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Caches (em memória; ids de sessão são únicos, então colisão é impossível)
# ---------------------------------------------------------------------------

# Páginas decodificadas, limitadas por LRU (páginas em resolução cheia são pesadas).
_page_img_cache: "OrderedDict[tuple[str, int], np.ndarray]" = OrderedDict()
_PAGE_IMG_CACHE_MAX = 6

# Payload de regiões por (session, page, mode).
_regions_cache: dict[tuple[str, int, str], dict] = {}

# Resultados de OCR por (session, page, mode, region_id).
_ocr_cache: dict[tuple[str, int, str, int], dict] = {}

# Thumbnails codificadas por (session, page, width).
_thumb_cache: dict[tuple[str, int, int], bytes] = {}

# Protege os caches acima (Flask roda com threads).
_cache_lock = threading.Lock()

# Ajustes de segmentação pro caminho clássico (fallback).
SEG_MIN_AREA = 120
SEG_MIN_FILL = 0.12
SEG_MAX_FILL = 0.85


# ---------------------------------------------------------------------------
# Cálculo compartilhado (usado tanto por /api/regions quanto por /api/ocr)
# ---------------------------------------------------------------------------

def _get_page_image(session_id: str, page: int) -> np.ndarray | None:
    key = (session_id, page)
    with _cache_lock:
        if key in _page_img_cache:
            _page_img_cache.move_to_end(key)
            return _page_img_cache[key]
    files = _session_pages(session_id)
    if not files or page < 1 or page > len(files):
        return None
    img = cv2.imread(str(files[page - 1]), cv2.IMREAD_COLOR)
    if img is None:
        return None
    with _cache_lock:
        _page_img_cache[key] = img
        while len(_page_img_cache) > _PAGE_IMG_CACHE_MAX:
            _page_img_cache.popitem(last=False)
    return img


def _compute_regions(session_id: str, page: int,
                     mode: str = DEFAULT_DETECTION_MODE) -> dict | None:
    """Detecta blocos de texto em uma página (detector DL + pós-processamento clássico).

    Retorna um payload com `width`, `height` (espaço da imagem original) e
    `regions` (lista de caixas no espaço da imagem original), ou None em caso de erro.
    """
    key = (session_id, page, mode)
    with _cache_lock:
        if key in _regions_cache:
            return _regions_cache[key]

    img = _get_page_image(session_id, page)
    if img is None:
        return None

    t0 = time.perf_counter()
    blocks = detect_blocks(img, device="cpu", mode=mode)
    dt = (time.perf_counter() - t0) * 1000

    payload = {
        "page": page,
        "width": img.shape[1],
        "height": img.shape[0],
        "regions": [b.to_dict() for b in blocks],
    }
    with _cache_lock:
        _regions_cache[key] = payload
        # Mantém os crops condicionados exatos que geraram esses ids de região
        # estáveis; senão uma chamada posterior de OCR/debug rodaria o detector
        # de novo e poderia ver uma ordenação diferente.
        _blocks_cache[key] = blocks
    log.info("regions: page=%s/%s mode=%s -> %d blocks in %.0fms",
             session_id, page, mode, len(blocks), dt)
    return payload


# Blocos detectados por (session, page, mode) já com crops prontos pra OCR,
# pra /api/ocr não precisar rodar detecção de novo. Limitado pelo LRU das regiões.
_blocks_cache: dict[tuple[str, int, str], list] = {}


def _compute_blocks(session_id: str, page: int,
                    mode: str = DEFAULT_DETECTION_MODE):
    key = (session_id, page, mode)
    with _cache_lock:
        if key in _blocks_cache:
            return _blocks_cache[key]
    img = _get_page_image(session_id, page)
    if img is None:
        return None
    blocks = detect_blocks(img, device="cpu", mode=mode)
    with _cache_lock:
        _blocks_cache[key] = blocks
    return blocks


def _find_block(session_id: str, page: int, region_id: int,
                mode: str = DEFAULT_DETECTION_MODE):
    blocks = _compute_blocks(session_id, page, mode)
    if blocks is None:
        return None
    return next((b for b in blocks if b.id == region_id), None)


def _request_mode(value: object) -> str | None:
    """Retorna um modo de avaliação válido, ou None se a entrada for inválida."""
    mode = DEFAULT_DETECTION_MODE if value is None else value
    return mode if isinstance(mode, str) and mode in DETECTION_MODES else None


# ---------------------------------------------------------------------------
# Fábrica do app
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = Flask(__name__, static_folder=None)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_routes(app)
    register_static(app)
    return app


# ---------------------------------------------------------------------------
# Rotas da API
# ---------------------------------------------------------------------------

def register_routes(app: Flask) -> None:
    @app.get("/api/health")
    def health() -> Response:
        return jsonify({
            "status": "ok",
            "ocr_available": MangaOcrService.instance().is_available(),
            "time": int(time.time()),
        })

    @app.post("/api/load")
    def api_load() -> Response:
        if "file" not in request.files:
            return jsonify({"error": "no file uploaded under field 'file'"}), 400
        f = request.files["file"]
        raw = f.read()
        if not raw:
            return jsonify({"error": "empty upload"}), 400
        session_id = secrets.token_urlsafe(8)
        try:
            vol = cbz.extract_cbz(raw, session_id, SESSIONS_DIR)
        except Exception as e:  # noqa: BLE001
            log.exception("extract_cbz failed: %s", e)
            return jsonify({"error": f"invalid CBZ: {e}"}), 400
        if not vol.page_files:
            return jsonify({"error": "no images found in archive"}), 400

        # Esquenta o modelo de OCR (e o detector de texto) em background
        # pra o primeiro hover já ser rápido.
        def _warm() -> None:
            MangaOcrService.instance().warm_up()
            try:
                get_detector(device="cpu").available
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=_warm, daemon=True).start()

        return jsonify({
            "session_id": vol.session_id,
            "pages": len(vol.page_files),
            "title": f.filename,
        })

    @app.get("/api/page/<session_id>/<int:page>")
    def api_page(session_id: str, page: int) -> Response:
        files = _session_pages(session_id)
        if not files:
            return jsonify({"error": "session not found"}), 404
        if page < 1 or page > len(files):
            return jsonify({"error": "page out of range"}), 404

        thumb_w = request.args.get("w", type=int)
        path = files[page - 1]
        if not thumb_w or thumb_w <= 0:
            return send_from_directory(path.parent, path.name)

        tkey = (session_id, page, thumb_w)
        with _cache_lock:
            cached = _thumb_cache.get(tkey)
        if cached is not None:
            return Response(cached, mimetype="image/jpeg")

        img = _get_page_image(session_id, page)
        if img is None:
            return jsonify({"error": "could not read page image"}), 500
        h, w = img.shape[:2]
        scale = thumb_w / w
        thumb = cv2.resize(img, (thumb_w, max(1, int(round(h * scale)))),
                           interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return jsonify({"error": "could not encode thumbnail"}), 500
        data = buf.tobytes()
        with _cache_lock:
            _thumb_cache[tkey] = data
        return Response(data, mimetype="image/jpeg")

    @app.post("/api/regions")
    def api_regions() -> Response:
        body = request.get_json(silent=True) or {}
        session_id = body.get("session_id")
        page = body.get("page")
        mode = _request_mode(body.get("mode"))
        if not isinstance(session_id, str) or not isinstance(page, int):
            return jsonify(
                {"error": "session_id (str) and page (int) required"}), 400
        if mode is None:
            return jsonify({"error": f"mode must be one of {DETECTION_MODES}"}), 400
        payload = _compute_regions(session_id, page, mode)
        if payload is None:
            return jsonify({"error": "session/page not found"}), 404
        return jsonify(payload)

    @app.post("/api/ocr")
    def api_ocr() -> Response:
        body = request.get_json(silent=True) or {}
        session_id = body.get("session_id")
        page = body.get("page")
        region_id = body.get("region_id")
        mode = _request_mode(body.get("mode"))
        if not (isinstance(session_id, str)
                and isinstance(page, int)
                and isinstance(region_id, int)):
            return jsonify(
                {"error": "session_id, page, region_id required"}), 400
        if mode is None:
            return jsonify({"error": f"mode must be one of {DETECTION_MODES}"}), 400

        ocr_key = (session_id, page, mode, region_id)
        with _cache_lock:
            if ocr_key in _ocr_cache:
                return jsonify(_ocr_cache[ocr_key])

        blocks = _compute_blocks(session_id, page, mode)
        if blocks is None:
            return jsonify({"error": "session/page not found"}), 404
        block = next((b for b in blocks if b.id == region_id), None)
        if block is None:
            return jsonify({"error": "region not found"}), 404

        empty = {
            "region_id": region_id, "text": "", "furigana": "", "romaji": "",
            "tokens": [], "kanji": [], "translation": "",
        }
        if not block.crops:
            return jsonify(empty)

        from PIL import Image
        text = ""
        for crop in block.crops:
            text += MangaOcrService.instance().recognize(crop)

        if text:
            reading = to_reading(text)
            analysis = analyze(text)
            kanji_data = kanji_lookup(analysis["kanji_chars"])
            translation = to_portuguese(text)
            result = {
                "region_id": region_id,
                "text": text,
                "furigana": reading["furigana"],
                "romaji": reading["romaji"],
                "tokens": analysis["tokens"],
                "kanji": kanji_data,
                "translation": translation,
            }
        else:
            result = empty
        with _cache_lock:
            _ocr_cache[ocr_key] = result
        return jsonify(result)

    @app.get("/api/region_image/<session_id>/<int:page>/<int:region_id>")
    def api_region_image(session_id: str, page: int, region_id: int) -> Response:
        mode = _request_mode(request.args.get("mode"))
        if mode is None:
            return jsonify({"error": f"mode must be one of {DETECTION_MODES}"}), 400
        block = _find_block(session_id, page, region_id, mode)
        if block is None:
            return jsonify({"error": "region not found"}), 404
        img = _get_page_image(session_id, page)
        if img is None:
            return jsonify({"error": "page not found"}), 404
        pad = 8
        y1 = max(0, block.y - pad)
        y2 = min(img.shape[0], block.y + block.h + pad)
        x1 = max(0, block.x - pad)
        x2 = min(img.shape[1], block.x + block.w + pad)
        crop = img[y1:y2, x1:x2]
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return jsonify({"error": "could not encode crop"}), 500
        return Response(buf.tobytes(), mimetype="image/jpeg")

    @app.post("/api/deck/export")
    def api_deck_export() -> Response:
        body = request.get_json(silent=True) or {}
        session_id = body.get("session_id")
        cards_data = body.get("cards", [])
        if not isinstance(session_id, str) or not isinstance(cards_data, list):
            return jsonify({"error": "session_id and cards required"}), 400

        payloads: list[CardPayload] = []
        for c in cards_data:
            mode = _request_mode(c.get("detection_mode"))
            if mode is None:
                continue
            block = _find_block(session_id, c.get("page", 0), c.get("region_id", 0), mode)
            if block is None:
                continue
            img = _get_page_image(session_id, c.get("page", 0))
            if img is None:
                continue
            pad = 8
            y1 = max(0, block.y - pad)
            y2 = min(img.shape[0], block.y + block.h + pad)
            x1 = max(0, block.x - pad)
            x2 = min(img.shape[1], block.x + block.w + pad)
            crop = img[y1:y2, x1:x2]
            ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                continue
            fname = f"card_p{c['page']}_r{c['region_id']}.jpg"
            payloads.append(CardPayload(
                page=c["page"],
                region_id=c["region_id"],
                text=c.get("text", ""),
                furigana=c.get("furigana", ""),
                romaji=c.get("romaji", ""),
                translation=c.get("translation", ""),
                kanji_notes=c.get("kanji_notes", ""),
                image_filename=fname,
                image_bytes=buf.tobytes(),
            ))

        apkg_bytes = build_apkg(payloads)
        return Response(
            apkg_bytes,
            mimetype="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=yomi_deck.apkg"},
        )

    @app.get("/api/debug/<stage>/<session_id>/<int:page>")
    def api_debug(stage: str, session_id: str, page: int) -> Response:
        files = _session_pages(session_id)
        if not files:
            return jsonify({"error": "session not found"}), 404
        if page < 1 or page > len(files):
            return jsonify({"error": "page out of range"}), 404
        available = list(pipeline_debug.STAGES) + sorted(pipeline_debug.CONDITIONING_STAGES)
        if stage not in pipeline_debug.STAGES and stage not in pipeline_debug.CONDITIONING_STAGES:
            return jsonify({
                "error": f"unknown stage {stage!r}",
                "available": available,
            }), 400
        mode = _request_mode(request.args.get("mode"))
        if mode is None:
            return jsonify({"error": f"mode must be one of {DETECTION_MODES}"}), 400
        try:
            if stage in pipeline_debug.CONDITIONING_STAGES:
                img = _get_page_image(session_id, page)
                blocks = _compute_blocks(session_id, page, mode)
                if img is None or blocks is None:
                    return jsonify({"error": "session/page not found"}), 404
                stage_img = pipeline_debug.conditioning_stage(stage, img, blocks)
            else:
                stage_img = pipeline_debug.STAGES[stage](files[page - 1])
        except Exception as e:  # noqa: BLE001
            log.exception("debug stage %s failed: %s", stage, e)
            return jsonify({"error": str(e)}), 500
        ok, buf = cv2.imencode(".png", stage_img)
        if not ok:
            return jsonify({"error": "could not encode image"}), 500
        return Response(buf.tobytes(), mimetype="image/png")


# ---------------------------------------------------------------------------
# Servir arquivos estáticos (build do frontend) — mensagem de fallback se o build não existir
# ---------------------------------------------------------------------------

def register_static(app: Flask) -> None:
    @app.get("/")
    def index() -> Response:
        if (FRONTEND_DIST / "index.html").exists():
            return send_from_directory(FRONTEND_DIST, "index.html")
        return Response(
            "<h1>Yomi backend is up.</h1>"
            "<p>For development, run <code>cd frontend && npm run dev</code> "
            "and open <a href='http://localhost:5173'>http://localhost:5173</a>.</p>",
            mimetype="text/html",
        )

    @app.get("/<path:path>")
    def spa_fallback(path: str) -> Response:
        if not FRONTEND_DIST.exists():
            return index()
        candidate = FRONTEND_DIST / path
        if candidate.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_pages(session_id: str) -> list[Path]:
    """Retorna a lista de arquivos de página de uma sessão, em ordem natural."""
    if not session_id or "/" in session_id or ".." in session_id:
        return []
    return cbz.list_pages(SESSIONS_DIR / session_id)


app = create_app()


if __name__ == "__main__":
    # Porta 5001: o macOS AirPlay Receiver (ControlCenter) ocupa *:5000 e
    # o Safari resolve `localhost` via IPv6 ::1, que cai no AirPlay, e não
    # neste servidor. A 5001 evita essa confusão toda.
    port = int(os.environ.get("YOMI_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
