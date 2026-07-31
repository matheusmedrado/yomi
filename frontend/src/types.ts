export interface TextRegion {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export type DetectionMode =
  | "baseline"
  | "median_restore"
  | "hybrid"
  | "pdi_only";

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

export type DebugStage =
  | "restoration_original"
  | "restoration_filtered"
  | "restoration_comparison"
  | "gray"
  | "mask"
  | "otsu"
  | "morphology"
  | "cc"
  | "watershed"
  | "conditioning_raw"
  | "conditioning_enhanced"
  | "conditioning_mask"
  | "conditioning_components"
  | "conditioning_projection"
  | "conditioning_final"
  | "conditioning_overlay";

export type AppView = "upload" | "reader";

export interface StudyCard {
  id: string;
  page: number;
  region_id: number;
  detection_mode: DetectionMode;
  text: string;
  furigana: string;
  romaji: string;
  translation: string;
  tokens: OcrToken[];
  kanji: KanjiInfo[];
  ts: number;
}
