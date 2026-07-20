import { Sidebar } from "../components/Sidebar";
import { PageViewer } from "../components/PageViewer";
import { DeckPanel } from "../components/DeckPanel";
import { FlashcardModal } from "../components/FlashcardModal";
import { YomiLogo } from "../components/YomiLogo";
import { useStore } from "../store";
import { ArrowLeft, Keyboard, Layers } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";

export function ReaderLayout() {
  const reset = useStore((s) => s.reset);
  const title = useStore((s) => s.title);
  const totalPages = useStore((s) => s.totalPages);
  const debugStage = useStore((s) => s.debugStage);
  const cards = useStore((s) => s.cards);
  const deckOpen = useStore((s) => s.deckOpen);
  const setDeckOpen = useStore((s) => s.setDeckOpen);
  const activeCardId = useStore((s) => s.activeCardId);
  const [helpOpen, setHelpOpen] = useState(false);

  useKeyboardShortcuts();

  return (
    <div className="h-full flex flex-col bg-paper relative overflow-hidden">
      {/* Background kanji watermark */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 0.03, scale: 1 }}
        transition={{ duration: 2, ease: [0.2, 0.7, 0.1, 1] }}
        className="absolute inset-0 flex items-center justify-center pointer-events-none select-none"
        aria-hidden="true"
      >
        <span
          className="font-serif font-bold text-ink"
          style={{ fontSize: "min(60vw, 60vh)", lineHeight: 1 }}
        >
          読
        </span>
      </motion.div>

      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.2, 0.7, 0.1, 1] }}
        className="relative z-10 h-14 border-b border-ink/8 bg-paper/95 backdrop-blur-sm flex items-center justify-between px-6 shrink-0"
      >
        <div className="flex items-center gap-4">
          <button
            onClick={reset}
            className="kd-btn-ghost hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
            title="Voltar para o início"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <YomiLogo size={32} />
          <span className="font-serif italic text-sm text-ink-muted">読み</span>
          <span className="h-4 w-px bg-ink/15" />
          <span className="font-serif italic text-sm text-ink truncate max-w-[320px]">
            {title || `${totalPages} páginas`}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {debugStage && (
            <span className="font-mono text-[10px] text-ink-muted uppercase tracking-smallcaps">
              debug · {debugStage}
            </span>
          )}
          <button
            onClick={() => setDeckOpen(!deckOpen)}
            className={[
              "kd-btn-ghost relative hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
              deckOpen ? "!text-ink underline underline-offset-4" : "",
            ].join(" ")}
            title="Deck de estudo"
          >
            <Layers className="h-4 w-4" />
            {cards.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-vermilion text-paper text-[9px] font-mono w-4 h-4 flex items-center justify-center rounded-full">
                {cards.length > 9 ? "9+" : cards.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setHelpOpen((b) => !b)}
            className="kd-btn-ghost hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
            title="Atalhos de teclado"
          >
            <Keyboard className="h-4 w-4" />
          </button>
        </div>
      </motion.header>

      <div className="relative z-10 flex-1 flex min-h-0">
        <Sidebar />
        <PageViewer />
        <AnimatePresence>{deckOpen && <DeckPanel />}</AnimatePresence>
      </div>

      <AnimatePresence>
        {helpOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setHelpOpen(false)}
            className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-6"
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.3, ease: [0.2, 0.7, 0.1, 1] }}
              className="bg-paper border border-ink/12 shadow-editorial-lg max-w-lg w-full overflow-hidden"
            >
              <div className="p-8 border-b border-ink/8 bg-paper-warm/30">
                <p className="font-serif italic text-xs text-ink-muted tracking-wide">読み · YOMI</p>
                <h3 className="kd-heading mt-2 text-2xl tracking-tight">Atalhos de teclado</h3>
              </div>
              <div className="p-8">
                <ul className="space-y-2.5">
                  {[
                    ["←", "Página anterior"],
                    ["→", "Próxima página"],
                    ["+", "Aumentar zoom"],
                    ["−", "Diminuir zoom"],
                    ["0", "Resetar zoom"],
                    ["b", "Mostrar todas as regiões"],
                    ["f", "Modo foco"],
                    ["d", "Ciclo de estágio de debug"],
                    ["Tab", "Próxima região de texto"],
                    ["Shift+Tab", "Região de texto anterior"],
                    ["Enter", "Criar card da região focada"],
                    ["Esc", "Fechar modal / Limpar foco"],
                    ["Espaço", "Virar card (no modal)"],
                  ].map(([k, d]) => (
                    <li key={k} className="flex items-center justify-between group">
                      <span className="text-sm text-ink-muted group-hover:text-ink transition-colors duration-150">{d}</span>
                      <kbd className="font-mono text-xs bg-paper-warm border border-ink/12 px-3 py-1.5 group-hover:border-ink/30 group-hover:bg-paper transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded">
                        {k}
                      </kbd>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {activeCardId && <FlashcardModal />}
      </AnimatePresence>
    </div>
  );
}
