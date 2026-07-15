# Yomi

> A manga reader with instant OCR for Japanese language immersion. Read, hover, learn.

Yomi is a desktop application built with Python and OpenCV for the *Digital Image
Processing* course at UFU (Universidade Federal de Uberlândia). It lets a Japanese
learner open real manga pages, hover over a speech bubble, and instantly see the
recognized text together with its reading (furigana/romaji) to support immersion
learning.

- **Course:** Processamento Digital de Imagens — UFU
- **Scope:** manga only (no anime, no novels)
- **Core principle:** every image operation is classical Digital Image Processing.
  No deep learning and no AI is used anywhere in the pipeline, including the OCR.

---

## 1. About

Yomi ("読み", *reading*) is a manga reader whose goal is to lower the friction of
reading Japanese as a learner. Instead of stopping to look words up manually, the
user hovers the mouse over a text region and Yomi:

1. detects the text region using a classical image-processing pipeline,
2. recognizes the characters with a classical, non-neural OCR,
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

## 3. No Deep Learning / AI Policy

Per the course requirements, **Yomi uses no deep learning and no AI for any part
of its processing**. This applies to the OCR stage as well:

- No neural OCR engines (e.g., manga-ocr, Tesseract LSTM mode) are used.
- Character recognition is performed with classical template matching and a
  k-nearest-neighbor classifier over a font-rendered template database.
- The reading layer uses `pykakasi`, a rule-based kana/kanji converter (a port
  of the classical `kakasi` system), not a language model.

This constraint shapes the architecture: the intelligence of the system lives in
the image-processing pipeline and the classical recognizer we implement, not in a
pretrained model.

---

## 4. Architecture

Yomi is a web application: a Python backend (Flask + OpenCV) serves a lightweight
frontend (HTML + Canvas) that runs in the browser. The heavy image work happens
server-side; the client only sends the page and the hovered region.

```
Manga page (PNG from a local CBZ)
        |
        v
+-------------------------------+
|  PDI Pre-processing pipeline  |   Labs 00, 03, 04, 05, 09
|  - grayscale, CLAHE, denoise, |
|    edge maps, color handling  |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Text region segmentation     |   Labs 02, 06, 07, 08
|  - Otsu threshold, morphology,|
|    connected components,      |
|    watershed (touching text)  |
+---------------+---------------+
                |  bounding boxes (text regions)
                v
   On hover: which box is under the cursor?
                |
                v
+-------------------------------+
|  Classical OCR (no DL)        |   Lab 02 + pattern recognition
|  - char segmentation          |
|  - normalization              |
|  - template match + k-NN      |
+---------------+---------------+
                |  recognized characters
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
- `POST /api/process` — receives a page image, runs the PDI pipeline, and returns
  the list of detected text-region bounding boxes.
- `POST /api/ocr` — receives a hovered region, runs the classical OCR and the
  reading layer, and returns the recognized text with its reading. OCR is invoked
  lazily on hover so the page stays responsive.

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

### 6.1 Classical OCR (no deep learning)

Because neural OCR is forbidden, recognition is implemented from classical
pattern-recognition building blocks:

1. **Character segmentation** — horizontal and vertical projection profiling
   combined with connected components (Lab 02) split each text region into
   individual character glyphs.
2. **Normalization** — each glyph is cropped to its bounding box, resized with
   aspect-ratio preservation to a fixed canvas, binarized, and centered using
   image moments (Lab 02). Optional deskew is applied when needed.
3. **Features** — two classical descriptors are combined:
   - *Normalized cross-correlation* against templates rendered from several
     common Japanese fonts.
   - A *zoning* feature vector (ink-density grid over the normalized glyph).
4. **Classification** — a **k-nearest-neighbor** classifier (classical ML, not a
   neural network) selects the best-matching glyph from a template database.
5. **Template database** — built offline by `build_templates.py`, which renders
   hiragana, katakana, and a curated set of common kanji from the fonts in
   `data/fonts/` into normalized reference glyphs.

To maximize accuracy on real, stylized manga fonts, templates are rendered from
multiple common Japanese fonts and the glyphs are strongly normalized before
matching. Recognition is best-effort: the value of the work is the pipeline and
the interaction, not OCR perfection (which only a neural model could approach,
and is excluded by the course rules).

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
- OpenCV (`cv2`) — image processing
- NumPy — array math
- Pillow (PIL) — font rendering for the template database
- `pykakasi` — rule-based reading conversion

**Frontend**

- HTML, CSS, and vanilla JavaScript
- Canvas for page display and `mousemove` hover detection

**OCR**

- Implemented in-house: projection + connected components, normalization,
  template matching, and k-NN classification. No external OCR engine.

---

## 9. Project Structure

```
yomi/
  README.md
  requirements.txt
  .gitignore
  backend/
    app.py                  # Flask server + API endpoints
    pipeline/
      __init__.py
      preprocess.py         # grayscale, CLAHE, denoise        (Labs 00,03,04)
      edges.py              # Sobel/Laplacian/Canny            (Lab 05)
      segmentation.py       # Otsu, morphology, conn. comps,  (Labs 02,06,07,08)
                             #   watershed
      ocr/
        __init__.py
        char_segment.py     # projection + connected components
        normalize.py        # glyph normalization
        features.py         # correlation + zoning features
        classifier.py       # k-NN over template DB
        templates.py        # load/query template database
        build_templates.py  # render glyph DB from fonts
    language.py             # pykakasi reading layer
    static/
      index.html
      reader.js
      style.css
    data/
      fonts/                # Japanese fonts for the template DB (gitignored binaries)
      samples/              # local manga pages / CBZ for presentation (NOT in git)
  tests/
  docs/
```

Note: the `data/samples/` directory (real manga pages used only in the local
presentation to the professor) and any CBZ archives are excluded from version
control. The repository contains no copyrighted material.

---

## 10. Getting Started

Prerequisites: Python 3.10+ and a Japanese font (e.g., Noto Sans JP) available
locally for the template database.

```bash
# 1. Clone the repository
git clone <repo-url>
cd yomi

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build the classical OCR template database
python backend/pipeline/ocr/build_templates.py

# 5. Run the backend
python backend/app.py

# 6. Open the reader in your browser
#    visit http://127.0.0.1:5000
```

Load your local CBZ (or a folder of pages) through the reader UI, then hover over
any speech bubble to see the recognized text and its reading.

*(Exact commands and ports are finalized during implementation.)*

---

## 11. Roadmap

- **Phase 1 — MVP (now):** CBZ/folder loading, PDI pipeline, classical OCR,
  hover overlay with reading, no AI anywhere.
- **Phase 2 — Richer learning:** dictionary meanings (JMdict/Jisho) and Anki
  export, prepared for in the current architecture.
- **Phase 3 — Full reader:** library/browsing across series, reading progress,
  additional color-page handling.

---

## 12. References

- [Manatan](https://github.com/KolbyML/Manatan) — inspiration for the hover-to-learn
  interaction (manga scope only).
- [OpenCV](https://opencv.org/) — image-processing library.
- [Pillow (PIL)](https://python-pillow.org/) — font rendering for templates.
- [pykakasi](https://github.com/miurahr/pykakasi) — rule-based Japanese reading
  conversion.
- [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) — Japanese dictionary
  (planned meaning lookup).
- Course material: `atividadesPraticas/` (Lab00–Lab09).

---

## 13. Team and License

Developed by Matheus Medrado Ferreira, Matheus de Andrade Tabchoury, Luiz
Henrique Rodrigues Ferreira, and Christian Silva Rodrigues for the Digital Image
Processing course at UFU.

Licensed under the MIT License.
