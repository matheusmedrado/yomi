import { motion } from "framer-motion";
import type { OcrResult } from "../types";
import { Sparkles } from "lucide-react";

interface TextOverlayProps {
  /** Screen (client) coordinates of the hovered region's top-right corner. */
  anchor: { x: number; y: number };
  result: OcrResult | null;
  loading: boolean;
}

const OVERLAY_W = 280;
const OVERLAY_EST_H = 160;
const GAP = 8;
const KANJI_RE = /[\u4E00-\u9FFF]/;

/**
 * Reading overlay. Anchored to the hovered region (not the raw cursor) so it
 * stays perfectly still while the user moves inside the box. The whole card
 * is `pointer-events-none` — it can never steal hover from the page, which
 * is what eliminates flicker.
 */
export function TextOverlay({ anchor, result, loading }: TextOverlayProps) {
  const flipX = anchor.x + OVERLAY_W + GAP > window.innerWidth - 12;
  const flipY = anchor.y + OVERLAY_EST_H + GAP > window.innerHeight - 12;

  const left = flipX ? anchor.x - OVERLAY_W - GAP : anchor.x + GAP;
  const top = flipY ? anchor.y - OVERLAY_EST_H : anchor.y + GAP;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, transition: { duration: 0.08 } }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      style={{ left, top, width: OVERLAY_W }}
      className="fixed z-40 pointer-events-none"
    >
      <div className="bg-ink text-paper shadow-editorial-lg">
        {loading ? (
          <div className="px-4 py-3 flex items-center gap-3">
            <div className="h-3 w-3 border border-paper border-t-transparent rounded-full animate-spin" />
            <span className="text-xs tracking-wide text-paper/80">
              recognizing…
            </span>
          </div>
        ) : result && result.text ? (
          <div className="p-4 space-y-2.5">
            <div className="flex items-center gap-2 text-paper/60">
              <Sparkles className="h-3 w-3" />
              <span className="kd-kicker !text-paper/60 !text-[10px]">
                Reading
              </span>
            </div>
            <p className="font-serif text-[17px] leading-relaxed">
              {Array.from(result.text).map((c, i) =>
                KANJI_RE.test(c) ? (
                  <span key={i} className="text-[#ff8093] font-medium">
                    {c}
                  </span>
                ) : (
                  <span key={i}>{c}</span>
                ),
              )}
            </p>
            {result.furigana && result.furigana !== result.text && (
              <p className="font-serif text-sm text-paper/85 leading-relaxed">
                {result.furigana}
              </p>
            )}
            {result.romaji && (
              <p className="font-mono text-[11px] text-paper/55 tracking-wide">
                {result.romaji}
              </p>
            )}
          </div>
        ) : (
          <div className="px-4 py-3 text-xs text-paper/60">
            no text recognized
          </div>
        )}
      </div>
    </motion.div>
  );
}
