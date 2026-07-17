import { Sidebar } from "../components/Sidebar";
import { PageViewer } from "../components/PageViewer";
import { HistoryPanel } from "../components/HistoryPanel";
import { YomiLogo } from "../components/YomiLogo";
import { useStore } from "../store";
import { ArrowLeft, Keyboard } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";

export function ReaderLayout() {
  const setView = useStore((s) => s.setView);
  const title = useStore((s) => s.title);
  const totalPages = useStore((s) => s.totalPages);
  const debugStage = useStore((s) => s.debugStage);
  const [helpOpen, setHelpOpen] = useState(false);

  useKeyboardShortcuts();

  return (
    <div className="h-full flex flex-col bg-paper">
      {/* Header */}
      <header className="h-12 border-b border-ink/10 bg-paper flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setView("upload")}
            className="kd-btn-ghost"
            title="Back to upload"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <YomiLogo size={28} />
          <span className="font-serif text-base">Yomi</span>
          <span className="h-4 w-px bg-ink/20" />
          <span className="text-xs text-ink-muted truncate max-w-[280px]">
            {title || `${totalPages} pages`}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {debugStage && (
            <span className="font-mono text-[10px] text-ink-muted uppercase tracking-smallcaps">
              debug · {debugStage}
            </span>
          )}
          <button
            onClick={() => setHelpOpen((b) => !b)}
            className="kd-btn-ghost"
            title="Keyboard shortcuts"
          >
            <Keyboard className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex min-h-0">
        <Sidebar />
        <PageViewer />
        <HistoryPanel />
      </div>

      <AnimatePresence>
        {helpOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setHelpOpen(false)}
            className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center"
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              initial={{ y: 8, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 8, opacity: 0 }}
              className="bg-paper border border-ink/20 shadow-editorial-lg p-8 max-w-md w-full"
            >
              <h3 className="kd-heading text-2xl">Keyboard shortcuts</h3>
              <span className="kd-divider mt-3 block" />
              <ul className="mt-4 space-y-2 text-sm">
                {[
                  ["←", "Previous page"],
                  ["→", "Next page"],
                  ["+", "Zoom in"],
                  ["−", "Zoom out"],
                  ["0", "Reset zoom"],
                  ["b", "Show all regions"],
                  ["f", "Focus mode"],
                  ["d", "Cycle debug stage"],
                ].map(([k, d]) => (
                  <li key={k} className="flex items-center justify-between">
                    <span className="text-ink-muted">{d}</span>
                    <kbd className="font-mono text-xs bg-paper-warm border border-ink/20 px-2 py-0.5">
                      {k}
                    </kbd>
                  </li>
                ))}
              </ul>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
