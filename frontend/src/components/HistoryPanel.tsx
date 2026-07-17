import { useStore } from "../store";
import { AnimatePresence, motion } from "framer-motion";
import { Trash2, BookOpen } from "lucide-react";

export function HistoryPanel() {
  const history = useStore((s) => s.history);
  const clearHistory = useStore((s) => s.clearHistory);
  const setCurrentPage = useStore((s) => s.setCurrentPage);

  return (
    <aside className="w-[260px] shrink-0 h-full bg-paper-warm border-l border-ink/10 flex flex-col">
      <div className="px-4 py-3 border-b border-ink/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-ink-muted" />
          <span className="kd-kicker">History</span>
        </div>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            className="text-ink-muted hover:text-vermilion transition-colors"
            title="Clear history"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        <AnimatePresence initial={false}>
          {history.length === 0 ? (
            <motion.p
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-ink-muted leading-relaxed px-1 pt-2"
            >
              Hover any speech bubble to start collecting readings.
            </motion.p>
          ) : (
            history.map((h) => (
              <motion.button
                key={`${h.page}:${h.region_id}`}
                layout
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.18 }}
                onClick={() => setCurrentPage(h.page)}
                className="w-full text-left bg-paper border border-ink/10 p-3 hover:border-ink/40 hover:bg-paper transition-colors"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[10px] text-ink-muted">
                    page {h.page}
                  </span>
                  <span className="font-mono text-[10px] text-ink-muted">
                    {new Date(h.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
                <p className="font-serif text-sm text-ink leading-snug">
                  {h.text}
                </p>
                {h.furigana && (
                  <p className="font-serif text-xs text-ink-muted mt-1">
                    {h.furigana}
                  </p>
                )}
                {h.romaji && (
                  <p className="font-mono text-[10px] text-ink-muted/70 mt-0.5">
                    {h.romaji}
                  </p>
                )}
              </motion.button>
            ))
          )}
        </AnimatePresence>
      </div>
    </aside>
  );
}
