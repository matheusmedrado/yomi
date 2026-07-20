import { motion } from "framer-motion";
import type { OcrResult, ScriptType } from "../types";
import { Sparkles, MousePointerClick } from "lucide-react";

interface TextOverlayProps {
  anchor: { x: number; y: number };
  result: OcrResult | null;
  loading: boolean;
}

const OVERLAY_W = 340;
const OVERLAY_EST_H = 260;
const GAP = 8;

const SCRIPT_COLORS: Record<ScriptType, string> = {
  kanji: "text-[#ff8093]",
  katakana: "text-[#8ab4ff]",
  hiragana: "text-paper",
  other: "text-paper/70",
};

const SCRIPT_LABELS: Record<ScriptType, string> = {
  hiragana: "あ ひらがな",
  katakana: "ア カタカナ",
  kanji: "漢 かんじ",
  other: "…",
};

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
              reconhecendo…
            </span>
          </div>
        ) : result && result.text ? (
          <div className="p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-paper/60">
                <Sparkles className="h-3 w-3" />
                <span className="kd-kicker !text-paper/60 !text-[10px]">
                  Leitura
                </span>
              </div>
              <div className="flex gap-1.5">
                {(["hiragana", "katakana", "kanji"] as ScriptType[]).map((s) => (
                  <span
                    key={s}
                    className={`text-[9px] font-mono ${SCRIPT_COLORS[s]} opacity-70`}
                  >
                    {SCRIPT_LABELS[s]}
                  </span>
                ))}
              </div>
            </div>

            <p className="font-serif text-[17px] leading-relaxed">
              {Array.from(result.text).map((c, i) => {
                const cp = c.charCodeAt(0);
                let script: ScriptType = "other";
                if (cp >= 0x4e00 && cp <= 0x9fff) script = "kanji";
                else if (cp >= 0x30a0 && cp <= 0x30ff) script = "katakana";
                else if (cp >= 0x3040 && cp <= 0x309f) script = "hiragana";
                return (
                  <span key={i} className={SCRIPT_COLORS[script]}>
                    {c}
                  </span>
                );
              })}
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

            {result.translation && (
              <div className="pt-1.5 border-t border-paper/10">
                <span className="kd-kicker !text-paper/40 !text-[9px]">
                  Tradução
                </span>
                <p className="text-sm text-paper/90 italic mt-0.5 leading-relaxed">
                  {result.translation}
                </p>
              </div>
            )}

            {result.kanji && result.kanji.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {result.kanji.slice(0, 6).map((k) => (
                  <span
                    key={k.char}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-paper/10 text-[11px] text-paper/80"
                    title={k.meanings_pt.join(", ") || k.meanings_en.join(", ")}
                  >
                    <span className="text-[#ff8093] font-serif">{k.char}</span>
                    <span className="text-paper/50 truncate max-w-[80px]">
                      {k.meanings_pt[0] || k.meanings_en[0] || ""}
                    </span>
                  </span>
                ))}
              </div>
            )}

            <div className="flex items-center gap-1.5 pt-1 text-paper/40">
              <MousePointerClick className="h-3 w-3" />
              <span className="text-[10px]">
                Clique para criar card de estudo
              </span>
            </div>
          </div>
        ) : (
          <div className="px-4 py-3 text-xs text-paper/60">
            nenhum texto reconhecido
          </div>
        )}
      </div>
    </motion.div>
  );
}
