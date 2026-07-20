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
    <div className="h-full flex flex-col bg-paper">
      <header className="h-12 border-b border-ink/10 bg-paper flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={reset}
            className="kd-btn-ghost"
            title="Voltar para o início"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <YomiLogo size={28} />
          <span className="font-serif text-base">Yomi</span>
          <span className="h-4 w-px bg-ink/20" />
          <span className="text-xs text-ink-muted truncate max-w-[280px]">
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
              "kd-btn-ghost relative",
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
            className="kd-btn-ghost"
            title="Atalhos de teclado"
          >
            <Keyboard className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
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
              <h3 className="kd-heading text-2xl">Atalhos de teclado</h3>
              <span className="kd-divider mt-3 block" />
              <ul className="mt-4 space-y-2 text-sm">
                {[
                  ["←", "Página anterior"],
                  ["→", "Próxima página"],
                  ["+", "Aumentar zoom"],
                  ["−", "Diminuir zoom"],
                  ["0", "Resetar zoom"],
                  ["b", "Mostrar todas as regiões"],
                  ["f", "Modo foco"],
                  ["d", "Ciclo de estágio de debug"],
                  ["Esc", "Fechar modal"],
                  ["Espaço", "Virar card (no modal)"],
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

      <AnimatePresence>
        {activeCardId && <FlashcardModal />}
      </AnimatePresence>
    </div>
  );
}
