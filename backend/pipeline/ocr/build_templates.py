from __future__ import annotations

import os
import pickle
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "templates_db", "templates.pkl")
CANVAS = 64
RENDER_SIZE = 96

HIRAGANA = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
                "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっゃゅょ")

KATAKANA = list("アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
                "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポッャュョヴ")

KANJI_N5 = list(set("一二三四五六七八九十百千万円時分週秒前後朝昼夜春夏秋冬年月日火水木金土天気雨雪空海山川"
                     "花草木虫魚鳥肉食飲買売話聞読書字名前会社人男女子母父兄姉弟友達学生先生上司外国人私中"
                     "日本語国公立大小高低長短新古若老白黒青赤色声音目耳鼻口手足体頭心肺血中気力心正反左右"
                     "東西南北内外中外出入返休仕事学教室旅店屋茶酒肉卵米麦道車電話番地地図北風好悪寒暑明暗"
                     "東京勉強方行猫都合間物店買食走路見思出開立回道具目玉歯舌頭首胸腹足腰手紙筆硯刀剣"))

FONT_CANDIDATES = [
    "/usr/share/fonts/noto-cjk",
    os.path.join(HERE, "..", "..", "data", "fonts"),
]


def _font_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _available_fonts() -> list[tuple[str, int, str]]:
    import glob

    found = []
    seen = set()
    for base in FONT_CANDIDATES:
        base = os.path.abspath(base)
        if not os.path.isdir(base):
            continue
        for path in sorted(glob.glob(os.path.join(base, "*.ttc"))) + sorted(
            glob.glob(os.path.join(base, "*.ttf"))
        ) + sorted(glob.glob(os.path.join(base, "*.otf"))):
            key = os.path.basename(path)
            if key in seen:
                continue
            seen.add(key)
            found.append((path, 0, _font_name(path)))
    if not found:
        raise FileNotFoundError(
            "Nenhuma fonte japonesa encontrada em " + str(FONT_CANDIDATES)
        )
    return found


def render_glyph(char: str, font: ImageFont.FreeTypeFont) -> np.ndarray:
    img = Image.new("L", (RENDER_SIZE + 40, RENDER_SIZE + 40), 255)
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), char, font=font, fill=0)
    return np.array(img, dtype=np.uint8)


def build_templates(db_path: str = DB_PATH) -> dict:
    from pipeline.ocr.bitmap import build_halo_packed, glyph_to_bitmap, _pack
    from pipeline.ocr.normalize import normalize_glyph

    fonts = _available_fonts()
    images: list[np.ndarray] = []
    labels: list[str] = []
    font_names: list[str] = []
    bitmaps_packed: list[np.ndarray] = []
    ref_pixels: list[int] = []
    ref_halos: list[list[np.ndarray]] = []

    chars = HIRAGANA + KATAKANA + KANJI_N5
    for path, index, fname in fonts:
        font = ImageFont.truetype(path, RENDER_SIZE, index=index)
        for char in chars:
            gray = render_glyph(char, font)
            if (gray < 128).sum() < 5:
                continue
            normalized = normalize_glyph(gray, size=CANVAS)
            if normalized.sum() < 20:
                continue
            bitmap = glyph_to_bitmap(normalized)
            images.append(normalized)
            labels.append(char)
            font_names.append(fname)
            bitmaps_packed.append(_pack(bitmap))
            ref_pixels.append(int(bitmap.sum()))
            ref_halos.append(build_halo_packed(bitmap))

    n = len(images)
    packed = np.stack(bitmaps_packed).astype(np.uint64)
    pixels = np.array(ref_pixels, dtype=np.int64)
    halos = [np.stack([ref_halos[i][layer] for i in range(n)]).astype(np.uint64)
             for layer in range(len(ref_halos[0]))]

    payload = {
        "images": np.stack(images).astype(np.uint8),
        "labels": labels,
        "fonts": font_names,
        "size": CANVAS,
        "chars": sorted(set(labels)),
        "bitmaps_packed": packed,
        "ref_pixels": pixels,
        "ref_halos": halos,
    }
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(db_path, "wb") as fh:
        pickle.dump(payload, fh)
    return payload


if __name__ == "__main__":
    result = build_templates()
    print(f"Templates gerados: {len(result['labels'])} glyphs")
    print(f"Caracteres unicos: {len(result['chars'])}")
    print(f"Salvo em: {DB_PATH}")
