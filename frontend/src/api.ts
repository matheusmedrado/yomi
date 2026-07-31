import type { DetectionMode, LoadResponse, OcrResult, RegionsResponse, StudyCard } from "./types";

const API = "/api";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function loadCbz(file: File): Promise<LoadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/load`, { method: "POST", body: form });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<LoadResponse>;
}

export function pageImageUrl(
  sessionId: string,
  page: number,
  w?: number,
): string {
  const base = `${API}/page/${sessionId}/${page}`;
  return w ? `${base}?w=${w}` : base;
}

export function regionImageUrl(
  sessionId: string,
  page: number,
  regionId: number,
  mode: DetectionMode = "hybrid",
): string {
  return `${API}/region_image/${sessionId}/${page}/${regionId}?mode=${mode}`;
}

export function debugImageUrl(
  sessionId: string,
  page: number,
  stage: string,
  mode: DetectionMode = "hybrid",
): string {
  return `${API}/debug/${stage}/${sessionId}/${page}?mode=${mode}`;
}

export function getRegions(
  sessionId: string,
  page: number,
  mode: DetectionMode = "hybrid",
): Promise<RegionsResponse> {
  return postJson<RegionsResponse>("/regions", {
    session_id: sessionId,
    page,
    mode,
  });
}

export function ocr(
  sessionId: string,
  page: number,
  regionId: number,
  mode: DetectionMode = "hybrid",
): Promise<OcrResult> {
  return postJson<OcrResult>("/ocr", {
    session_id: sessionId,
    page,
    region_id: regionId,
    mode,
  });
}

export async function exportDeck(
  sessionId: string,
  cards: StudyCard[],
): Promise<Blob> {
  const res = await fetch(`${API}/deck/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      cards: cards.map((c) => ({
        page: c.page,
        region_id: c.region_id,
        detection_mode: c.detection_mode,
        text: c.text,
        furigana: c.furigana,
        romaji: c.romaji,
        translation: c.translation,
        kanji_notes: c.kanji
          .map(
            (k) =>
              `${k.char}: ${k.meanings_pt.join(", ")} | kun: ${k.kun.join(", ")} | on: ${k.on.join(", ")}`,
          )
          .join("\n"),
      })),
    }),
  });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status} ${res.statusText}`);
  }
  return res.blob();
}
