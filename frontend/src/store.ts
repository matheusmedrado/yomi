import { create } from "zustand";
import type { OcrResult, TextRegion, AppView, DebugStage } from "./types";

export interface HistoryEntry extends OcrResult {
  page: number;
  ts: number;
}

interface UiState {
  // View
  view: AppView;
  setView: (v: AppView) => void;

  // Session
  sessionId: string | null;
  title: string | null;
  totalPages: number;
  currentPage: number;
  setSession: (s: { sessionId: string; pages: number; title?: string }) => void;
  setCurrentPage: (p: number) => void;

  // Image natural size per page (for coordinate mapping)
  pageSizeByPage: Record<number, { w: number; h: number }>;
  setPageSize: (page: number, s: { w: number; h: number }) => void;

  // Regions per page (cached in-memory)
  regionsByPage: Record<number, TextRegion[]>;
  setRegions: (page: number, regions: TextRegion[]) => void;

  // OCR cache: key = `${page}:${regionId}` -> OcrResult
  ocrCache: Record<string, OcrResult>;
  cacheOcr: (key: string, result: OcrResult) => void;

  // History (in-session)
  history: HistoryEntry[];
  pushHistory: (entry: HistoryEntry) => void;
  clearHistory: () => void;

  // UI toggles
  showAllBoxes: boolean;
  focusMode: boolean;
  debugStage: DebugStage | null;
  toggleShowAllBoxes: () => void;
  toggleFocusMode: () => void;
  setDebugStage: (s: DebugStage | null) => void;

  // Loading flags
  uploading: boolean;
  uploadError: string | null;
  setUploading: (b: boolean) => void;
  setUploadError: (e: string | null) => void;

  // Reset
  reset: () => void;
}

const initial = {
  view: "upload" as AppView,
  sessionId: null as string | null,
  title: null as string | null,
  totalPages: 0,
  currentPage: 1,
  pageSizeByPage: {} as Record<number, { w: number; h: number }>,
  regionsByPage: {} as Record<number, TextRegion[]>,
  ocrCache: {} as Record<string, OcrResult>,
  history: [] as HistoryEntry[],
  showAllBoxes: false,
  focusMode: false,
  debugStage: null as DebugStage | null,
  uploading: false,
  uploadError: null as string | null,
};

export const useStore = create<UiState>((set) => ({
  ...initial,

  setView: (v) => set({ view: v }),

  setSession: ({ sessionId, pages, title }) =>
    set({
      sessionId,
      totalPages: pages,
      title: title ?? null,
      currentPage: 1,
      pageSizeByPage: {},
      regionsByPage: {},
      ocrCache: {},
      history: [],
    }),

  setCurrentPage: (p) => set({ currentPage: p }),
  setPageSize: (page, s) =>
    set((st) => ({
      pageSizeByPage: { ...st.pageSizeByPage, [page]: s },
    })),

  setRegions: (page, regions) =>
    set((s) => ({
      regionsByPage: { ...s.regionsByPage, [page]: regions },
    })),

  cacheOcr: (key, result) =>
    set((s) => ({ ocrCache: { ...s.ocrCache, [key]: result } })),

  pushHistory: (entry) =>
    set((s) => {
      // dedupe by page+region
      const without = s.history.filter(
        (h) => !(h.page === entry.page && h.region_id === entry.region_id),
      );
      return { history: [entry, ...without].slice(0, 50) };
    }),

  clearHistory: () => set({ history: [] }),

  toggleShowAllBoxes: () => set((s) => ({ showAllBoxes: !s.showAllBoxes })),
  toggleFocusMode: () => set((s) => ({ focusMode: !s.focusMode })),
  setDebugStage: (s) => set({ debugStage: s }),

  setUploading: (b) => set({ uploading: b }),
  setUploadError: (e) => set({ uploadError: e }),

  reset: () => set({ ...initial }),
}));
