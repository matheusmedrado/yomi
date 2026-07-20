# Yomi

> A manga reader with instant OCR for Japanese language immersion. Read, hover, learn.

Yomi is a desktop application built with Python and OpenCV for the *Digital Image
Processing* course at UFU (Universidade Federal de Uberlândia). It lets a Japanese
learner open real manga pages, hover over a speech bubble, and instantly see the
recognized text together with its reading (furigana/romaji) to support immersion
learning.

- **Course:** Processamento Digital de Imagens — UFU
- **Scope:** manga only (no anime, no novels)
- **Core principle:** the image-processing stages (pre-processing and the
  post-processing that feeds the recognizer) are classical Digital Image
  Processing (Labs 02, 06, 07). Text *localization* — the one step classical
  PDI genuinely cannot do on real artwork — uses a learned detector, as detailed
  in §3.

## 🎬 Demo

[![Yomi Demo](https://img.youtube.com/vi/OMmOtloOp4I/maxresdefault.jpg)](https://youtu.be/OMmOtloOp4I)

*Assista a demonstração completa no YouTube*

---

## 1. About

Yomi ("読み", *reading*) is a manga reader whose goal is to lower the friction of
reading Japanese as a learner. Instead of stopping to look words up manually, the
user hovers the mouse over a text region and Yomi:

1. detects the text region using a text detector,
2. recognizes the characters with a transformer OCR,
3. shows the recognized string and its reading (furigana/romaji) in an overlay.

The project is developed by:

- Matheus Medrado Ferreira
- Matheus de Andrade Tabchoury
- Luiz Henrique Rodrigues Ferreira
- Christian Silva Rodrigues

The interaction concept is inspired by [Manatan](https://github.com/KolbyML/Manatan),
an open-source immersion tool. Yomi narrows that idea to manga and rebuilds the
image processing from first principles using the techniques studied in the course.

---

## 2. Motivation

Reading raw manga is hard for language learners: vocabulary is unknown, kanji
readings are ambiguous, and stopping to consult a dictionary breaks immersion.
Existing tools that solve this well rely on deep-learning OCR, which is out of
scope for this course.

Yomi demonstrates that a useful, interactive reading aid can be built entirely
from classical Digital Image Processing: sampling, filtering, thresholding,
morphology, connected components, watershed, and classical pattern recognition.
The result helps learners while staying true to the course's foundations.

---

## 3. Deep Learning / AI Policy

Per the course requirements, the **image processing** in Yomi is classical
Digital Image Processing — sampling, filtering, thresholding, morphology,
connected components, watershed, and classical pattern recognition. These
stages are the core of the work and they remain DL-free:

- **Pre-processing (classical):** grayscale, CLAHE contrast equalization,
  denoise, color→ink mask, Otsu binarization (Labs 02, 06, 07).
- **Post-processing (classical):** after a text block is located, it is split
  into OCR-sized chunks using a **classical ink-density cut** — the refined text
  mask's density profile is smoothed with a Gaussian window (Lab 07) and cut at
  the local minima between characters/lines. This is the same idea mokuro uses,
- **Reading layer (classical):** `pykakasi`, a rule-based kana/kanji converter
  (a port of the classical `kakasi` system), not a language model.

The two **deep-learning** components are isolated, off-the-shelf, and explicitly
authorized for this final project:

- **Text localization** uses
  [comic-text-detector](https://github.com/dmMaze/comic-text-detector) — the
  same DBNet/YOLO detector mokuro uses. This is the *only* stage where classical
  PDI fails on real pages: blob/connected-component analysis cannot tell text
  ink from artwork ink (dragons, screentone, speedlines), producing hundreds of
  false-positive boxes on art. We therefore localize text with the detector and
  keep the classical PDI work on the stages around it.
- **Recognition (OCR)** uses
  [manga-ocr](https://github.com/kha-white/manga-ocr), a Vision Encoder-Decoder
  transformer trained specifically on manga text. It handles vertical text,
  small furigana and stylized fonts out of the box.

This shapes the architecture: the intelligence of the system lives in the
**classical pre/post-processing pipeline** wrapping two black-box models, exactly
the split used in real detection-then-recognition systems.

---

## 4. Architecture

Yomi is a web application: a Python backend (Flask + OpenCV + manga-ocr) serves
a lightweight frontend (HTML + Canvas) that runs in the browser. The heavy image
work happens server-side; the client only sends the page and the hovered region.

```
Manga page (PNG uploaded from the browser as a CBZ)
        |
        v
+-------------------------------+
|  PDI Pre-processing pipeline  |   Labs 00, 03, 04, 05, 06, 07, 09
|  - grayscale, CLAHE, denoise, |
|    Otsu binarize, edge maps,  |
|    color handling             |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Text localization (DL)       |   comic-text-detector
|  - DBNet/YOLO text detector   |   (same as mokuro)
|  - returns text blocks        |
+---------------+---------------+
                |  bounding boxes (text blocks)
                v
+-------------------------------+
|  PDI post-processing (split)  |   Labs 02, 07
|  - classical ink-density cut  |
|    (Gaussian-smoothed minima) |
|    splits blocks into chunks  |
+---------------+---------------+
                |  OCR-ready crops
                v
+-------------------------------+
|  manga-ocr (authorized DL)    |   recognition black box
|  - transformer encoder-decoder|
|    trained on manga text      |
+---------------+---------------+
                |  recognized string
                v
+-------------------------------+
|  Language layer (pykakasi)    |   rule-based
|  - furigana / romaji reading  |
+---------------+---------------+
                |
                v
        Overlay shown on hover
```

**Backend API**

- `GET /` — serves the reader page.
- `POST /api/load` — receives an uploaded CBZ (zip) from the browser, extracts
  the page images into a session directory, and returns the page count.
- `GET /api/page/<session_id>/<n>` — returns the PNG of page `n`.
- `POST /api/regions` — `{session_id, page}` runs detection and returns the list
  of detected text-region bounding boxes (cached per page). Blocks are split into
  OCR-ready crops by the classical density cut.
- `POST /api/ocr` — `{session_id, page, region_id}` runs manga-ocr on the
  pre-cut crops of the hovered region and the reading layer, returning the
  recognized text with its reading. OCR is invoked lazily on hover.
- `GET /api/debug/<stage>/<session_id>/<n>` — returns an intermediate image
  (Otsu mask, connected components, watershed, etc.) for the debug view.

---

## 5. Image Processing Pipeline

The pipeline is the core of the project and maps directly onto the practical
activities (`atividadesPraticas`) developed during the course.

| Lab | Technique | Role in Yomi |
|-----|-----------|--------------|
| 00 | numpy / OpenCV / matplotlib | Image I/O, array handling, and visualization/debugging of every stage. |
| 01 | Sampling & Quantization | Control input resolution/DPI via resizing so the OCR receives a consistent scale. |
| 02 | Connected Components | Label and filter candidate regions by area/aspect ratio to keep text and discard noise; also used for character-level segmentation. |
| 03 | Histogram Equalization (CLAHE) | Improve contrast of faded or poorly scanned pages before binarization. |
| 04 | Low-pass Filtering | Gaussian / median blur to suppress noise before thresholding. |
| 05 | High-pass Filtering | Sobel / Laplacian / Canny edge maps that help locate text boundaries. |
| 06 | Thresholding (Otsu) | Automatic ink/paper separation via `cv2.threshold` with `THRESH_OTSU`. |
| 07 | Mathematical Morphology | Opening/closing and dilation/erosion (`cv2.morphologyEx`) to clean the binary mask and close broken strokes. |
| 08 | Watershed | Separate touching text lines/characters when connected components merge them. |
| 09 | Color | Color-space handling (`cv2.cvtColor`) for color pages: detect speech bubbles and ignore painted backgrounds. |

Each stage is implemented as an independently testable function so the effect of
the technique can be demonstrated and graded on its own.

---

## 6. OCR and Language Layer

### 6.1 Recognition (manga-ocr)

With the professor's authorization, the recognition stage is delegated to
[manga-ocr](https://github.com/kha-white/manga-ocr), a Vision Encoder-Decoder
model trained specifically on manga text. It is loaded lazily on the first
`/api/ocr` call, which means the PDI-only endpoints stay available even when
the model is not (e.g., for grading the classical pipeline in isolation).

The work in front of the recognizer matters: manga-ocr expects a **tight crop
of a single speech bubble or text block**, so the quality of the upstream
segmentation directly drives recognition quality.

### 6.2 Language layer

- `pykakasi` (rule-based) converts the recognized string into furigana/romaji
  reading shown in the hover overlay.
- *(Planned)* Dictionary meanings via JMdict (local) or the Jisho API.
- *(Planned)* One-click Anki card export for sentence mining.

---

## 7. Features

**Current (MVP)**

- Load a local CBZ file (or a folder of pages) and extract its PNG pages.
- Page navigation and zoom in the reader.
- Hover over a text region to get instant classical OCR + reading overlay.
- Fully classical pipeline: no deep learning, no AI.

**Planned**

- Richer dictionary lookup (meanings) via JMdict / Jisho.
- Anki card export for immersion sentence mining.
- Library/browsing mode across multiple series and CBZ archives.

---

## 8. Tech Stack

**Backend**

- Python 3
- Flask (web server and API)
- OpenCV (`cv2`) — classical image processing (pipeline)
- NumPy — array math
- Pillow (PIL) — image I/O helpers
- `pykakasi` — rule-based reading conversion
- `manga-ocr` (transformer, runs on MPS on Apple Silicon) — recognition stage,
  the only DL component, authorized by the professor

**Frontend**

- React 18 + TypeScript + Vite
- Tailwind CSS for design tokens
- Zustand for state, Framer Motion for transitions, lucide-react for icons
- Visual language inspired by kodansha.us (editorial black/white with a
  single vermilion accent, Noto Serif JP for the 読 logo and headings,
  Inter for UI, smallcaps kickers)
- Functional inspiration: mokuro (sidebar of pages, viewer with hover
  overlay, per-page region detection)

**OCR**

- `manga-ocr` for recognition. The classical PDI pipeline handles every step
  before that: preprocessing, thresholding, morphology, connected components,
  watershed, and text-region clustering.

---

## 9. Project Structure

```
yomi/
  README.md
  PLAN.md                   # execution plan / roadmap
  requirements.txt
  .gitignore
  backend/
    app.py                  # Flask server + API endpoints
    cbz.py                  # CBZ/zip extraction from upload
    ocr.py                  # manga-ocr wrapper (lazy singleton)
    language.py             # pykakasi reading layer
    pipeline/
      __init__.py
      preprocess.py         # grayscale, CLAHE, denoise        (Labs 00,03,04,09)
      edges.py              # Sobel/Laplacian/Canny            (Lab 05)
      segmentation.py       # Otsu, morphology, conn. comps,  (Labs 02,06,07,08)
                             #   watershed, line clustering
      debug.py              # dump intermediate stages for the debug view
    sessions/               # per-upload page dirs (gitignored)
  frontend/                 # React + Vite app (see frontend/README.md)
    src/                    # components, views, store, API client
    public/                 # favicon / static assets
    package.json
    vite.config.ts          # dev: proxies /api -> :5001
  tests/
    conftest.py
    test_preprocess.py
    test_edges.py
    test_segmentation.py
    test_language.py
    test_ocr.py             # skip-safe smoke test for the manga-ocr wrapper
  docs/
    PLAN.md
```

Note: the `data/samples/` directory (real manga pages used only in the local
presentation to the professor) and any CBZ archives are excluded from version
control. The repository contains no copyrighted material.

---

## 10. Getting Started

Prerequisites: Python 3.10+, Node 18+, and a working network connection (the
first run of `manga-ocr` downloads the recognition model from HuggingFace,
~440 MB; the browser uploads manga pages as CBZ archives).

### One-shot demo (single port)

```bash
git clone <repo-url>
cd yomi

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend (built)
cd frontend && npm install && npm run build && cd ..

# (Optional) warm up manga-ocr so the first hover is not slow
python -c "from backend.ocr import MangaOcrService; MangaOcrService().warm_up()"

# Run
python backend/app.py
# open http://127.0.0.1:5001
```

### Day-to-day development (Vite + Flask, hot reload)

Open two terminals.

```bash
# terminal 1: backend
.venv/bin/python backend/app.py        # serves API on :5001

# terminal 2: frontend
cd frontend && npm run dev             # serves Vite on :5173, proxies /api -> :5001
# open http://localhost:5173
```

Upload a local CBZ through the reader UI, then hover over any speech bubble to
see the recognized text and its reading. Press `d` to cycle through the
debug stages of the classical PDI pipeline, `b` to show all detected regions,
and `f` to dim the rest of the page while reading a single bubble. The
`?` button (or `K` shortcut via the help modal) lists all shortcuts.

---

## 11. Roadmap

See `docs/PLAN.md` for the current 2-week execution plan. In short:

- **Phase 1 — MVP (now):** upload of CBZ via the browser, classical PDI
  pipeline, manga-ocr recognition, hover overlay with reading.
- **Phase 2 — Richer learning:** dictionary meanings (JMdict/Jisho) and Anki
  export, prepared for in the current architecture.
- **Phase 3 — Full reader:** library/browsing across series, reading progress,
  additional color-page handling.

---

## 12. References

- [Manatan](https://github.com/KolbyML/Manatan) — inspiration for the hover-to-learn
  interaction (manga scope only).
- [OpenCV](https://opencv.org/) — image-processing library.
- [Pillow (PIL)](https://python-pillow.org/) — image helpers.
- [pykakasi](https://github.com/miurahr/pykakasi) — rule-based Japanese reading
  conversion.
- [manga-ocr](https://github.com/kha-white/manga-ocr) — transformer OCR trained
  on manga text, used for the recognition stage.
- [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) — Japanese dictionary
  (planned meaning lookup).
- Course material: `atividadesPraticas/` (Lab00–Lab09).

---

## 13. Team and License

Developed by Matheus Medrado Ferreira, Matheus de Andrade Tabchoury, Luiz
Henrique Rodrigues Ferreira, and Christian Silva Rodrigues for the Digital Image
Processing course at UFU.

Licensed under the MIT License.
