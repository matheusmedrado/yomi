# Plano de Execução — Yomi (v2)

> Plano vivo. Ajustar conforme a equipe avança.

## 0. Contexto e mudanças

- O plano original previa OCR 100% clássico (template matching + k-NN).
- O **professor autorizou** o uso do `manga-ocr` (encoder-decoder treinado em mangá,
  com suporte nativo a texto vertical e fontes estilizadas).
- O sistema continua sendo um **web app** (Flask + HTML/JS/Canvas).
- A parte clássica de PDI (pré-processamento, segmentação, leitura via pykakasi)
  permanece **100% clássica** — é o que será avaliado.

Arquiteturalmente: o **pipeline de PDI** agora é responsável por toda a
**detecção/segmentação das regiões de texto**, e o `manga-ocr` entra apenas como
caixa-preta de reconhecimento no final — divisão detecção vs. reconhecimento,
como sistemas reais.

## 1. Decisão de OCR

| Opção      | Mangá vertical | Precisão geral | Esforço | Veredito |
|------------|:--------------:|:--------------:|:-------:|----------|
| Tesseract (legado) | ruim    | baixa          | -       | descartado |
| EasyOCR    | fraco          | média          | médio   | descartado |
| PaddleOCR  | médio          | média          | pesado  | descartado |
| **manga-ocr** | **ótimo**   | **alta**       | **baixo** | **escolhido** |
| mokuro     | ótimo (usa manga-ocr) | alta  | baixo   | alternativa de UI, mas o modelo de hover é melhor para PDI |

## 2. Estrutura alvo

```
yomi/
  README.md                    # atualizado: política, arquitetura, stack, setup
  PLAN.md                      # este documento
  requirements.txt             # + manga-ocr (puxa torch/transformers)
  backend/
    app.py                     # Flask + API
    cbz.py                     # extração de CBZ/zip
    ocr.py                     # wrapper manga-ocr (lazy singleton)
    language.py                # pykakasi → furigana/romaji
    pipeline/
      preprocess.py            # to_grayscale, resize, CLAHE, denoise, color mask
      edges.py                 # sobel, laplacian, canny
      segmentation.py          # otsu, morphology, CC, watershed, cluster_lines
      debug.py                 # dump de estágios para visualização (demo/nota)
    static/  (index.html, reader.js, style.css)
    data/samples/              # gitignored
  tests/
    conftest.py                # simplificado (remover template DB)
    test_preprocess.py         # manter
    test_edges.py              # manter
    test_segmentation.py       # manter
    test_language.py           # manter
    test_ocr.py                # NOVO (skip se modelo indisponível)
    # REMOVIDOS: test_classifier.py, test_features.py, test_normalize.py
```

## 3. Cronograma (14 dias)

### Fase 0 — Setup + docs (dias 1–2)
- [x] Atualizar `requirements.txt` (incluir `manga-ocr`).
- [x] Gerar `docs/PLAN.md` (este).
- [x] Atualizar `README.md` (seções 3, 4, 6, 8, 9, 10).
- [x] Limpar testes obsoletos (`test_classifier.py`, `test_features.py`,
      `test_normalize.py`) e o `conftest.py`.
- [x] Instalar deps em `.venv` (Flask, OpenCV, NumPy, Pillow, pykakasi, pytest,
      `Flask-Cors`, `manga-ocr` + `torch` + `transformers`).
- [x] Modelo do `manga-ocr` (~440MB) baixado do HuggingFace e warm-up
      funcionando (MPS no Apple Silicon, ~200ms por inferência).

### Fase 1 — Pipeline PDI (núcleo avaliado) (dias 1–5)
- [x] `preprocess.py`: `to_grayscale`, `resize_longest_edge`, `clahe_equalize`,
      `denoise`, `color_to_text_mask`, `preprocess_page`.
- [x] `edges.py`: `sobel`, `laplacian`, `canny`.
- [x] `segmentation.py`: `otsu_threshold`, `morphology_cleanup`,
      `connected_components`, `TextRegion`, `cluster_lines`,
      `detect_text_regions` + **watershed** p/ texto colado.
- [x] `pytest` verde nos 3 módulos clássicos (18/18 passando).
- [x] Cada estágio como função independentemente testável.
- [x] `debug.py`: dumps de estágios (gray, mask, otsu, cc, watershed) servidos
      via `/api/debug/<stage>/...` para a UI.

### Fase 2 — OCR + idioma (dias 5–7)
- [x] `ocr.py`: `MangaOcr` lazy singleton; `recognize(crop_bgr) -> str`
      (BGR → PIL, padding de ~10px no crop). Carregamento lazy garante que
      `/api/regions` (PDI puro) funcione mesmo sem o modelo — bom para avaliar
      a parte clássica isoladamente.
- [x] `language.py`: `to_reading` com pykakasi (testes já passam).
- [x] Cache em memória dos resultados por (página, região) para hover instantâneo
      (no cliente Zustand; servidor cacheia regions por página).
- [x] `tests/test_ocr.py`: smoke tests skip-safe; 1 teste real roda quando o
      modelo está disponível.

### Fase 3 — API Flask (dias 7–9)
- [x] `GET /api/health` — liveness + flag `ocr_available`.
- [x] `POST /api/load` — upload de CBZ, extrai p/ `backend/sessions/<sid>/`.
- [x] `GET /api/page/<session_id>/<n>` — JPEG da página.
- [x] `POST /api/regions` — PDI pipeline → `[{id, x, y, w, h}]` em coords
      originais (mapeado a partir do gray redimensionado).
- [x] `POST /api/ocr` — crop + padding → manga-ocr → pykakasi.
- [x] `GET /api/debug/<stage>/<session_id>/<n>` — imagens de estágios.
- [x] Flask serve o `frontend/dist/` em produção (com fallback dev-friendly
      em desenvolvimento).

### Fase 4 — Frontend React + Kodansha vibe (dias 9–12)
- [x] Bootstrap: Vite + React 18 + TypeScript + Tailwind + Zustand +
      Framer Motion + lucide-react.
- [x] Identidade Kodansha: preto/off-white + acent vermilion, Inter (UI)
      + Noto Serif JP (logo 読み + tipografia editorial), smallcaps
      uppercase p/ kickers, "By [Author]" byline pattern.
- [x] Tela de upload: dropzone animada, logo 読, gridlines decorativas,
      3 cards numerados "Open / Hover / Read".
- [x] Reader layout: sidebar (páginas em grid), viewer (img + SVG overlay
      de boxes), painel de histórico à direita.
- [x] PageViewer: hit-test por hover, overlay SVG com `framer-motion`,
      focus mask (escurece o resto), debug blend dos estágios, zoom/pan.
- [x] TextOverlay: card preto com texto kanji (cada kanji destacado e
      clicável para "kanji breakdown"), furigana, romaji.
- [x] HistoryPanel: cards das frases OCRadas nesta sessão, clicar
      navega até a página.
- [x] Atalhos: ←/→, b, f, d (cycle de estágios debug), help modal.
- [x] Vite dev: `:5173` com proxy → Flask `:5000`.
- [x] Vite build: Flask serve `frontend/dist/` em `/`.

### Fase 5 — Integração e polimento da demo (dias 12–14)
- [x] Backend rodando, manga-ocr warm, OCR real chamado via API.
- [x] `pytest` completo: **22/22 passando** (clássico + smoke OCR).
- [ ] Testar com mangás reais (locais, gitignored): ajustar `min_area`, kernels
      de morfologia, filtros de aspect ratio. **Ponto de atenção:** texto
      vertical — `manga-ocr` reconhece nativamente, mas o `cluster_lines` precisa
      agrupar **colunas** (não só linhas) para o crop sair correto. Flag
      `vertical=True` já está no `cluster_lines` e em `detect_text_regions`;
      falta UI toggle e tuning com material real.
- [ ] Roteiro da demo: upload → modo debug (estágios) → boxes → hover com OCR.

## 4. Riscos e cuidados

| Risco | Mitigação |
|---|---|
| torch/manga-ocr ~2GB de deps + download do modelo | Instalar e aquecer no dia 1; modelo fica em cache no HuggingFace |
| Compatibilidade numpy 2 × transformers | Testar no setup; se quebrar, pinar `numpy<2` |
| 1ª inferência lenta (CPU) | Warm-up no boot do servidor ou no 1º `/api/load`; UI mostra loading |
| Segmentação ruim → OCR ruim | É aqui que o esforço de PDI vai: dias 12–14 só de tuning com páginas reais |
| Material com copyright | Samples só locais (já coberto no `.gitignore`) |

## 5. Entrada de páginas

- **Upload pelo navegador** (drag & drop de CBZ). É o caminho "web app" de fato
  e funciona em qualquer máquina na demo.
- O backend extrai as páginas em um diretório de sessão temporário e as serve
  via `GET /api/page/<session_id>/<n>`.

## 6. Critérios de pronto (MVP)

- [ ] Upload de CBZ pelo navegador.
- [ ] Detecção de regiões de texto 100% clássica (Otsu + morfologia + CC + watershed).
- [ ] Hover sobre região → OCR com manga-ocr + leitura com pykakasi.
- [ ] `pytest` verde nos módulos clássicos.
- [ ] Modo debug mostrando os estágios do pipeline (peso para nota).
- [ ] README atualizado com nova política e comandos reais.
