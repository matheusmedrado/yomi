import { create } from "zustand";
import type { OcrResult, TextRegion, AppView, DebugStage, StudyCard } from "./types";

interface UiState {
  view: AppView;
  setView: (v: AppView) => void;

  sessionId: string | null;
  title: string | null;
  totalPages: number;
  currentPage: number;
  setSession: (s: { sessionId: string; pages: number; title?: string }) => void;
  setCurrentPage: (p: number) => void;

  pageSizeByPage: Record<number, { w: number; h: number }>;
  setPageSize: (page: number, s: { w: number; h: number }) => void;

  regionsByPage: Record<number, TextRegion[]>;
  setRegions: (page: number, regions: TextRegion[]) => void;

  ocrCache: Record<string, OcrResult>;
  cacheOcr: (key: string, result: OcrResult) => void;

  cards: StudyCard[];
  addCard: (card: StudyCard) => void;
  removeCard: (id: string) => void;
  clearCards: () => void;

  deckOpen: boolean;
  setDeckOpen: (b: boolean) => void;
  activeCardId: string | null;
  setActiveCardId: (id: string | null) => void;

  showAllBoxes: boolean;
  focusMode: boolean;
  debugStage: DebugStage | null;
  toggleShowAllBoxes: () => void;
  toggleFocusMode: () => void;
  setDebugStage: (s: DebugStage | null) => void;

  uploading: boolean;
  uploadError: string | null;
  setUploading: (b: boolean) => void;
  setUploadError: (e: string | null) => void;

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
  cards: [] as StudyCard[],
  deckOpen: false,
  activeCardId: null as string | null,
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
      cards: [],
      deckOpen: false,
      activeCardId: null,
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

  addCard: (card) =>
    set((s) => {
      const exists = s.cards.some((c) => c.id === card.id);
      if (exists) return s;
      return { cards: [card, ...s.cards] };
    }),

  removeCard: (id) =>
    set((s) => ({
      cards: s.cards.filter((c) => c.id !== id),
      activeCardId: s.activeCardId === id ? null : s.activeCardId,
    })),

  clearCards: () => set({ cards: [], activeCardId: null }),

  deckOpen: false,
  setDeckOpen: (b) => set({ deckOpen: b }),
  activeCardId: null,
  setActiveCardId: (id) => set({ activeCardId: id }),

  toggleShowAllBoxes: () => set((s) => ({ showAllBoxes: !s.showAllBoxes })),
  toggleFocusMode: () => set((s) => ({ focusMode: !s.focusMode })),
  setDebugStage: (s) => set({ debugStage: s }),

  setUploading: (b) => set({ uploading: b }),
  setUploadError: (e) => set({ uploadError: e }),

  reset: () => set({ ...initial }),
}));
