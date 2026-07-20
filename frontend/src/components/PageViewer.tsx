import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { useStore } from "../store";
import { debugImageUrl, getRegions, ocr, pageImageUrl } from "../api";
import { TextOverlay } from "./TextOverlay";
import { Eye, EyeOff, Focus, ScanSearch } from "lucide-react";
import type { TextRegion } from "../types";

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 5;
const DEBUG_ORDER = ["otsu", "mask", "cc", "watershed"] as const;
const CLICK_THRESHOLD = 6;
const CLICK_TIME = 400;

const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));

export function PageViewer() {
  const sessionId = useStore((s) => s.sessionId)!;
  const currentPage = useStore((s) => s.currentPage);
  const setCurrentPage = useStore((s) => s.setCurrentPage);
  const totalPages = useStore((s) => s.totalPages);
  const pageSize = useStore((s) => s.pageSizeByPage[currentPage]) ?? null;
  const setPageSize = useStore((s) => s.setPageSize);
  const regions = useStore((s) => s.regionsByPage[currentPage]) ?? EMPTY;
  const setRegions = useStore((s) => s.setRegions);
  const ocrCache = useStore((s) => s.ocrCache);
  const cacheOcr = useStore((s) => s.cacheOcr);
  const addCard = useStore((s) => s.addCard);
  const setActiveCardId = useStore((s) => s.setActiveCardId);
  const showAllBoxes = useStore((s) => s.showAllBoxes);
  const toggleShowAllBoxes = useStore((s) => s.toggleShowAllBoxes);
  const focusMode = useStore((s) => s.focusMode);
  const toggleFocusMode = useStore((s) => s.toggleFocusMode);
  const debugStage = useStore((s) => s.debugStage);
  const setDebugStage = useStore((s) => s.setDebugStage);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [keyboardFocusId, setKeyboardFocusId] = useState<number | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);

  const stageRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const panRef = useRef(pan);
  panRef.current = pan;
  const dragRef = useRef<{
    startX: number;
    startY: number;
    baseX: number;
    baseY: number;
    time: number;
  } | null>(null);
  const hoverRef = useRef<number | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    if (useStore.getState().regionsByPage[currentPage]) return;
    let cancelled = false;
    getRegions(sessionId, currentPage)
      .then((res) => {
        if (cancelled) return;
        setRegions(currentPage, res.regions);
        setPageSize(currentPage, { w: res.width, h: res.height });
      })
      .catch(() => {
        // Regions failed to load - will retry on next page change
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, currentPage, setRegions, setPageSize]);

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    hoverRef.current = null;
    setHoverId(null);
    setKeyboardFocusId(null);
  }, [currentPage]);

  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const dir = e.deltaY < 0 ? 1 : -1;
      setZoom((z) => clamp(z * (1 + dir * 0.12), MIN_ZOOM, MAX_ZOOM));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail;
      if (detail === "in") setZoom((z) => clamp(z * 1.15, MIN_ZOOM, MAX_ZOOM));
      if (detail === "out") setZoom((z) => clamp(z / 1.15, MIN_ZOOM, MAX_ZOOM));
      if (detail === "reset") {
        setZoom(1);
        setPan({ x: 0, y: 0 });
      }
    };
    window.addEventListener("yomi:zoom", handler);
    return () => window.removeEventListener("yomi:zoom", handler);
  }, []);

  const hitTest = useCallback(
    (clientX: number, clientY: number): number | null => {
      const img = imgRef.current;
      if (!img || !pageSize) return null;
      const rect = img.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      const nx = ((clientX - rect.left) / rect.width) * pageSize.w;
      const ny = ((clientY - rect.top) / rect.height) * pageSize.h;
      if (nx < 0 || ny < 0 || nx >= pageSize.w || ny >= pageSize.h) {
        return null;
      }
      for (const r of regions) {
        if (nx >= r.x && nx <= r.x + r.w && ny >= r.y && ny <= r.y + r.h) {
          return r.id;
        }
      }
      return null;
    },
    [pageSize, regions],
  );

  const ensureOcr = useCallback(
    (regionId: number) => {
      const key = `${currentPage}:${regionId}`;
      if (useStore.getState().ocrCache[key]) return;
      setLoadingId(regionId);
      ocr(sessionId, currentPage, regionId)
        .then((res) => {
          cacheOcr(key, res);
        })
        .catch(() =>
          cacheOcr(key, {
            region_id: regionId,
            text: "",
            furigana: "",
            romaji: "",
            tokens: [],
            kanji: [],
            translation: "",
          }),
        )
        .finally(() =>
          setLoadingId((cur) => (cur === regionId ? null : cur)),
        );
    },
    [sessionId, currentPage, cacheOcr],
  );

  const navigateRegion = useCallback(
    (direction: "next" | "prev") => {
      if (regions.length === 0) return;

      const currentIndex = keyboardFocusId
        ? regions.findIndex((r) => r.id === keyboardFocusId)
        : -1;

      let nextIndex: number;
      if (direction === "next") {
        nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % regions.length;
      } else {
        nextIndex =
          currentIndex === -1
            ? regions.length - 1
            : (currentIndex - 1 + regions.length) % regions.length;
      }

      const nextRegion = regions[nextIndex];
      setKeyboardFocusId(nextRegion.id);
      ensureOcr(nextRegion.id);
    },
    [regions, keyboardFocusId, ensureOcr],
  );

  const clearKeyboardFocus = useCallback(() => {
    setKeyboardFocusId(null);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.key === "Tab") {
        e.preventDefault();
        navigateRegion(e.shiftKey ? "prev" : "next");
      } else if (e.key === "Escape") {
        clearKeyboardFocus();
      } else if (e.key === "Enter" && keyboardFocusId !== null) {
        e.preventDefault();
        const key = `${currentPage}:${keyboardFocusId}`;
        const result = useStore.getState().ocrCache[key];
        if (result && result.text) {
          const cardId = `${sessionId}:${currentPage}:${keyboardFocusId}`;
          addCard({
            id: cardId,
            page: currentPage,
            region_id: keyboardFocusId,
            text: result.text,
            furigana: result.furigana,
            romaji: result.romaji,
            translation: result.translation,
            tokens: result.tokens,
            kanji: result.kanji,
            ts: Date.now(),
          });
          setActiveCardId(cardId);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    navigateRegion,
    clearKeyboardFocus,
    keyboardFocusId,
    currentPage,
    sessionId,
    addCard,
    setActiveCardId,
  ]);

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      baseX: panRef.current.x,
      baseY: panRef.current.y,
      time: Date.now(),
    };
    setDragging(false);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (dragRef.current) {
      const d = dragRef.current;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      if (Math.abs(dx) > CLICK_THRESHOLD || Math.abs(dy) > CLICK_THRESHOLD) {
        setDragging(true);
        setPan({ x: d.baseX + dx, y: d.baseY + dy });
      }
      return;
    }
    const id = hitTest(e.clientX, e.clientY);
    if (id !== hoverRef.current) {
      hoverRef.current = id;
      setHoverId(id);
      if (id !== null) ensureOcr(id);
    }
  };

  const onPointerUp = (e: React.PointerEvent) => {
    const d = dragRef.current;
    dragRef.current = null;
    setDragging(false);
    if (!d) return;
    const elapsed = Date.now() - d.time;
    const dx = Math.abs(e.clientX - d.startX);
    const dy = Math.abs(e.clientY - d.startY);
    if (dx < CLICK_THRESHOLD && dy < CLICK_THRESHOLD && elapsed < CLICK_TIME) {
      const id = hitTest(e.clientX, e.clientY);
      if (id !== null) {
        const key = `${currentPage}:${id}`;
        const result = useStore.getState().ocrCache[key];
        if (result && result.text) {
          const cardId = `${sessionId}:${currentPage}:${id}`;
          addCard({
            id: cardId,
            page: currentPage,
            region_id: id,
            text: result.text,
            furigana: result.furigana,
            romaji: result.romaji,
            translation: result.translation,
            tokens: result.tokens,
            kanji: result.kanji,
            ts: Date.now(),
          });
          setActiveCardId(cardId);
        }
      }
    }
  };

  const onPointerLeave = () => {
    hoverRef.current = null;
    setHoverId(null);
    dragRef.current = null;
    setDragging(false);
  };

  // Determine active region (hover takes priority over keyboard focus)
  const activeId = hoverId ?? keyboardFocusId;
  const activeRegion: TextRegion | null =
    regions.find((r) => r.id === activeId) ?? null;

  let anchor: { x: number; y: number } | null = null;
  if (activeRegion && imgRef.current && pageSize) {
    const rect = imgRef.current.getBoundingClientRect();
    anchor = {
      x:
        rect.left +
        ((activeRegion.x + activeRegion.w) / pageSize.w) * rect.width,
      y: rect.top + (activeRegion.y / pageSize.h) * rect.height,
    };
  }

  const cacheKey = activeId !== null ? `${currentPage}:${activeId}` : null;
  const currentResult = cacheKey ? ocrCache[cacheKey] ?? null : null;
  const overlayLoading =
    activeId !== null && loadingId === activeId && !currentResult;

  return (
    <div className="relative flex-1 h-full bg-ink/[0.03] overflow-hidden">
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-paper/95 backdrop-blur border border-ink/10 shadow-editorial px-1.5 py-1.5">
        <button
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="kd-btn-ghost disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Anterior (←)"
        >
          ←
        </button>
        <span className="font-mono text-[11px] text-ink-muted px-2 min-w-[64px] text-center">
          {String(currentPage).padStart(2, "0")} /{" "}
          {String(totalPages).padStart(2, "0")}
        </span>
        <button
          onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage >= totalPages}
          className="kd-btn-ghost disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Próxima (→)"
        >
          →
        </button>
        <span className="w-px h-5 bg-ink/15 mx-1" />
        <button
          onClick={() => setZoom((z) => clamp(z / 1.15, MIN_ZOOM, MAX_ZOOM))}
          className="kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Diminuir zoom (-)"
        >
          −
        </button>
        <span className="font-mono text-[11px] text-ink-muted px-1 min-w-[44px] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => clamp(z * 1.15, MIN_ZOOM, MAX_ZOOM))}
          className="kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Aumentar zoom (+)"
        >
          +
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Resetar (0)"
        >
          0
        </button>
        <span className="w-px h-5 bg-ink/15 mx-1" />
        <button
          onClick={toggleShowAllBoxes}
          className={[
            "kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
            showAllBoxes ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Mostrar todas as regiões (b)"
        >
          {showAllBoxes ? (
            <Eye className="h-4 w-4" />
          ) : (
            <EyeOff className="h-4 w-4" />
          )}
        </button>
        <button
          onClick={toggleFocusMode}
          className={[
            "kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
            focusMode ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Modo foco (f)"
        >
          <Focus className="h-4 w-4" />
        </button>
        <button
          onClick={() => {
            if (debugStage === null) {
              setDebugStage(DEBUG_ORDER[0]);
            } else {
              const idx = DEBUG_ORDER.indexOf(
                debugStage as (typeof DEBUG_ORDER)[number],
              );
              setDebugStage(
                idx >= 0 && idx < DEBUG_ORDER.length - 1
                  ? DEBUG_ORDER[idx + 1]
                  : null,
              );
            }
          }}
          className={[
            "kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
            debugStage ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Estágios de debug (d)"
        >
          <ScanSearch className="h-4 w-4" />
        </button>
      </div>

      <div
        ref={stageRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerLeave}
        className={[
          "absolute inset-0 flex items-center justify-center select-none touch-none",
          dragging ? "cursor-grabbing" : hoverId !== null ? "cursor-pointer" : "cursor-grab",
        ].join(" ")}
      >
        <div
          className="relative"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
          }}
        >
          <img
            ref={imgRef}
            src={pageImageUrl(sessionId, currentPage)}
            alt={`Página ${currentPage}`}
            draggable={false}
            onLoad={(e) => {
              const el = e.currentTarget;
              const prev = useStore.getState().pageSizeByPage[currentPage];
              if (
                !prev ||
                prev.w !== el.naturalWidth ||
                prev.h !== el.naturalHeight
              ) {
                setPageSize(currentPage, {
                  w: el.naturalWidth,
                  h: el.naturalHeight,
                });
              }
            }}
            className="max-h-[88vh] max-w-[88vw] block shadow-editorial-lg"
          />

          {pageSize && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox={`0 0 ${pageSize.w} ${pageSize.h}`}
            >
              {regions.map((r) => {
                const isHovered = hoverId === r.id;
                const isKeyboardFocused = keyboardFocusId === r.id;
                const isActive = isHovered || isKeyboardFocused;
                const visible = isActive || showAllBoxes;
                return (
                  <rect
                    key={r.id}
                    x={r.x}
                    y={r.y}
                    width={r.w}
                    height={r.h}
                    fill={
                      isActive ? "rgba(200,16,46,0.10)" : "rgba(200,16,46,0)"
                    }
                    stroke={
                      isKeyboardFocused
                        ? "#4a90e2"
                        : isHovered
                          ? "var(--vermilion, #c8102e)"
                          : showAllBoxes
                            ? "rgba(10,10,10,0.45)"
                            : "rgba(200,16,46,0)"
                    }
                    strokeWidth={isActive ? 2.5 : 1.5}
                    strokeDasharray={
                      isKeyboardFocused
                        ? "4 2"
                        : showAllBoxes && !isActive
                          ? "7 5"
                          : undefined
                    }
                    vectorEffect="non-scaling-stroke"
                    style={{
                      opacity: visible ? 1 : 0,
                      transition: "opacity 120ms ease-out",
                    }}
                  />
                );
              })}
            </svg>
          )}

          {focusMode && activeRegion && pageSize && (
            <FocusMask region={activeRegion} pageSize={pageSize} />
          )}

          {debugStage && (
            <img
              src={debugImageUrl(sessionId, currentPage, debugStage)}
              alt={`Estágio: ${debugStage}`}
              draggable={false}
              className="absolute inset-0 w-full h-full object-fill mix-blend-multiply opacity-90 pointer-events-none"
            />
          )}
        </div>
      </div>

      <AnimatePresence>
        {anchor && (
          <TextOverlay
            anchor={anchor}
            result={currentResult}
            loading={overlayLoading}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

const EMPTY: TextRegion[] = [];

function FocusMask({
  region,
  pageSize,
}: {
  region: TextRegion;
  pageSize: { w: number; h: number };
}) {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox={`0 0 ${pageSize.w} ${pageSize.h}`}
    >
      <defs>
        <mask id="focus-mask">
          <rect width={pageSize.w} height={pageSize.h} fill="white" />
          <rect
            x={region.x}
            y={region.y}
            width={region.w}
            height={region.h}
            fill="black"
          />
        </mask>
      </defs>
      <rect
        width={pageSize.w}
        height={pageSize.h}
        fill="rgba(10,10,10,0.55)"
        mask="url(#focus-mask)"
      />
    </svg>
  );
}
