export interface TextRegion {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export type ScriptType = "hiragana" | "katakana" | "kanji" | "other";

export interface OcrToken {
  surface: string;
  furigana: string;
  romaji: string;
  script: ScriptType;
}

export interface KanjiInfo {
  char: string;
  meanings_pt: string[];
  meanings_en: string[];
  kun: string[];
  on: string[];
  strokes: number;
  grade: number;
  jlpt: number;
}

export interface OcrResult {
  region_id: number;
  text: string;
  furigana: string;
  romaji: string;
  tokens: OcrToken[];
  kanji: KanjiInfo[];
  translation: string;
}

export interface LoadResponse {
  session_id: string;
  pages: number;
  title?: string;
}

export interface RegionsResponse {
  page: number;
  width: number;
  height: number;
  regions: TextRegion[];
}

export type DebugStage = "gray" | "mask" | "otsu" | "cc" | "watershed";

export type AppView = "upload" | "reader";

export interface StudyCard {
  id: string;
  page: number;
  region_id: number;
  text: string;
  furigana: string;
  romaji: string;
  translation: string;
  tokens: OcrToken[];
  kanji: KanjiInfo[];
  ts: number;
}
