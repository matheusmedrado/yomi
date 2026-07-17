// Shared TypeScript types between the backend Flask API and the React app.

export interface TextRegion {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface OcrResult {
  region_id: number;
  text: string;
  furigana: string;
  romaji: string;
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
