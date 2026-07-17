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
  const pushHistory = useStore((s) => s.pushHistory);
  const showAllBoxes = useStore((s) => s.showAllBoxes);
  const toggleShowAllBoxes = useStore((s) => s.toggleShowAllBoxes);
  const focusMode = useStore((s) => s.focusMode);
  const toggleFocusMode = useStore((s) => s.toggleFocusMode);
  const debugStage = useStore((s) => s.debugStage);
  const setDebugStage = useStore((s) => s.setDebugStage);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hoverId, setHoverId] = useState<number | null>(null);
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
  } | null>(null);
  const hoverRef = useRef<number | null>(null);

  // ---- data ------------------------------------------------------------

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
      .catch((e) => console.error("getRegions failed", e));
    return () => {
      cancelled = true;
    };
  }, [sessionId, currentPage, setRegions, setPageSize]);

  // ---- view reset on page change ---------------------------------------

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    hoverRef.current = null;
    setHoverId(null);
  }, [currentPage]);

  // ---- zoom: native wheel (non-passive) + keyboard events --------------

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

  // ---- hit-testing ------------------------------------------------------
  //
  // `img.getBoundingClientRect()` already reflects CSS transforms (pan,
  // zoom), so mapping client coords into image-natural coords is exact and
  // immune to drift. This is what keeps the hover rock solid.

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

  // ---- OCR (once per region, cache-first) -------------------------------

  const ensureOcr = useCallback(
    (regionId: number) => {
      const key = `${currentPage}:${regionId}`;
      if (useStore.getState().ocrCache[key]) return;
      setLoadingId(regionId);
      ocr(sessionId, currentPage, regionId)
        .then((res) => {
          cacheOcr(key, res);
          if (res.text) {
            pushHistory({ ...res, page: currentPage, ts: Date.now() });
          }
        })
        .catch(() =>
          cacheOcr(key, {
            region_id: regionId,
            text: "",
            furigana: "",
            romaji: "",
          }),
        )
        .finally(() =>
          setLoadingId((cur) => (cur === regionId ? null : cur)),
        );
    },
    [sessionId, currentPage, cacheOcr, pushHistory],
  );

  // ---- pointer handlers -------------------------------------------------

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      baseX: panRef.current.x,
      baseY: panRef.current.y,
    };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (dragRef.current) {
      const d = dragRef.current;
      setPan({
        x: d.baseX + (e.clientX - d.startX),
        y: d.baseY + (e.clientY - d.startY),
      });
      return;
    }
    const id = hitTest(e.clientX, e.clientY);
    if (id !== hoverRef.current) {
      hoverRef.current = id;
      setHoverId(id);
      if (id !== null) ensureOcr(id);
    }
  };

  const endInteraction = () => {
    dragRef.current = null;
    setDragging(false);
  };

  const onPointerLeave = () => {
    hoverRef.current = null;
    setHoverId(null);
    endInteraction();
  };

  // ---- derived render state ---------------------------------------------

  const hoverRegion: TextRegion | null =
    regions.find((r) => r.id === hoverId) ?? null;

  let anchor: { x: number; y: number } | null = null;
  if (hoverRegion && imgRef.current && pageSize) {
    const rect = imgRef.current.getBoundingClientRect();
    anchor = {
      x:
        rect.left +
        ((hoverRegion.x + hoverRegion.w) / pageSize.w) * rect.width,
      y: rect.top + (hoverRegion.y / pageSize.h) * rect.height,
    };
  }

  const cacheKey = hoverId !== null ? `${currentPage}:${hoverId}` : null;
  const currentResult = cacheKey ? ocrCache[cacheKey] ?? null : null;
  const overlayLoading =
    hoverId !== null && loadingId === hoverId && !currentResult;

  return (
    <div className="relative flex-1 h-full bg-ink/[0.03] overflow-hidden">
      {/* Top toolbar */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-paper/95 backdrop-blur border border-ink/10 shadow-editorial px-1.5 py-1.5">
        <button
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="kd-btn-ghost disabled:opacity-30"
          title="Previous (←)"
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
          className="kd-btn-ghost disabled:opacity-30"
          title="Next (→)"
        >
          →
        </button>
        <span className="w-px h-5 bg-ink/15 mx-1" />
        <button
          onClick={() => setZoom((z) => clamp(z / 1.15, MIN_ZOOM, MAX_ZOOM))}
          className="kd-btn-ghost"
          title="Zoom out (-)"
        >
          −
        </button>
        <span className="font-mono text-[11px] text-ink-muted px-1 min-w-[44px] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => clamp(z * 1.15, MIN_ZOOM, MAX_ZOOM))}
          className="kd-btn-ghost"
          title="Zoom in (+)"
        >
          +
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="kd-btn-ghost"
          title="Reset (0)"
        >
          0
        </button>
        <span className="w-px h-5 bg-ink/15 mx-1" />
        <button
          onClick={toggleShowAllBoxes}
          className={[
            "kd-btn-ghost",
            showAllBoxes ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Show all regions (b)"
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
            "kd-btn-ghost",
            focusMode ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Focus mode (f)"
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
            "kd-btn-ghost",
            debugStage ? "!text-ink underline underline-offset-4" : "",
          ].join(" ")}
          title="Debug stages (d)"
        >
          <ScanSearch className="h-4 w-4" />
        </button>
      </div>

      {/* Stage */}
      <div
        ref={stageRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endInteraction}
        onPointerLeave={onPointerLeave}
        className={[
          "absolute inset-0 flex items-center justify-center select-none touch-none",
          dragging ? "cursor-grabbing" : "cursor-grab",
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
            alt={`Page ${currentPage}`}
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
                const visible = isHovered || showAllBoxes;
                return (
                  <rect
                    key={r.id}
                    x={r.x}
                    y={r.y}
                    width={r.w}
                    height={r.h}
                    fill={
                      isHovered ? "rgba(200,16,46,0.10)" : "rgba(200,16,46,0)"
                    }
                    stroke={
                      isHovered
                        ? "#c8102e"
                        : showAllBoxes
                          ? "rgba(10,10,10,0.45)"
                          : "rgba(200,16,46,0)"
                    }
                    strokeWidth={isHovered ? 2.5 : 1.5}
                    strokeDasharray={showAllBoxes && !isHovered ? "7 5" : undefined}
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

          {focusMode && hoverRegion && pageSize && (
            <FocusMask region={hoverRegion} pageSize={pageSize} />
          )}

          {debugStage && (
            <img
              src={debugImageUrl(sessionId, currentPage, debugStage)}
              alt={`Stage: ${debugStage}`}
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
