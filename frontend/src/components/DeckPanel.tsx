import { useStore } from "../store";
import { AnimatePresence, motion } from "framer-motion";
import { X, Download, Trash2, Layers } from "lucide-react";
import { exportDeck, regionImageUrl } from "../api";
import { useState } from "react";

export function DeckPanel() {
  const cards = useStore((s) => s.cards);
  const sessionId = useStore((s) => s.sessionId);
  const deckOpen = useStore((s) => s.deckOpen);
  const setDeckOpen = useStore((s) => s.setDeckOpen);
  const setActiveCardId = useStore((s) => s.setActiveCardId);
  const removeCard = useStore((s) => s.removeCard);
  const clearCards = useStore((s) => s.clearCards);
  const [exporting, setExporting] = useState(false);
  const [showConfirmClear, setShowConfirmClear] = useState(false);

  const handleExport = async () => {
    if (!sessionId || cards.length === 0) return;
    setExporting(true);
    try {
      const blob = await exportDeck(sessionId, cards);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "yomi_deck.apkg";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // Export failed silently - user can retry
    } finally {
      setExporting(false);
    }
  };

  if (!deckOpen) return null;

  return (
    <motion.aside
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ duration: 0.2, ease: [0.2, 0.7, 0.1, 1] }}
      className="w-[300px] shrink-0 h-full bg-paper-warm border-l border-ink/10 flex flex-col"
    >
      <div className="px-4 py-3 border-b border-ink/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-ink-muted" />
          <span className="kd-kicker">Deck de Estudo</span>
          <span className="font-mono text-[10px] text-ink-muted">
            {cards.length}
          </span>
        </div>
        <button
          onClick={() => setDeckOpen(false)}
          className="kd-btn-ghost focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          title="Fechar deck"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        <AnimatePresence initial={false}>
          {cards.length === 0 ? (
            <motion.p
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-ink-muted leading-relaxed px-1 pt-2"
            >
              Clique em um balão de fala para criar cards de estudo.
            </motion.p>
          ) : (
            cards.map((c) => (
              <motion.div
                key={c.id}
                layout
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.18 }}
                className="bg-paper border border-ink/10 hover:border-ink/40 transition-colors"
              >
                <button
                  onClick={() => setActiveCardId(c.id)}
                  className="w-full text-left p-3 focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
                >
                  <div className="flex items-start gap-3">
                    {sessionId && (
                      <img
                        src={regionImageUrl(
                          sessionId,
                          c.page,
                          c.region_id,
                        )}
                        alt={`Região de texto da página ${c.page}`}
                        className="w-12 h-12 object-cover shrink-0 border border-ink/10"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-serif text-sm text-ink leading-snug truncate">
                        {c.text}
                      </p>
                      {c.translation && (
                        <p className="text-xs text-ink-muted mt-0.5 truncate italic">
                          {c.translation}
                        </p>
                      )}
                      <p className="font-mono text-[10px] text-ink-muted/60 mt-1">
                        pág. {String(c.page).padStart(2, "0")}
                      </p>
                    </div>
                  </div>
                </button>
                <div className="px-3 pb-2 flex justify-end">
                  <button
                    onClick={() => removeCard(c.id)}
                    className="text-ink-muted hover:text-vermilion focus:text-vermilion focus:outline-none focus:ring-2 focus:ring-vermilion/50 transition-colors p-1 rounded"
                    title="Remover card"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {cards.length > 0 && (
        <div className="px-4 py-3 border-t border-ink/10 space-y-2">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="kd-btn w-full justify-center focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          >
            <Download className="h-4 w-4" />
            {exporting ? "Exportando…" : "Exportar .apkg (Anki)"}
          </button>
          <button
            onClick={() => setShowConfirmClear(true)}
            className="kd-btn-ghost w-full text-center text-vermilion text-xs focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
          >
            Limpar deck
          </button>
        </div>
      )}

      <AnimatePresence>
        {showConfirmClear && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowConfirmClear(false)}
            className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-6"
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.3, ease: [0.2, 0.7, 0.1, 1] }}
              className="bg-paper border border-ink/12 shadow-editorial-lg max-w-sm w-full overflow-hidden"
            >
              <div className="p-8 border-b border-ink/8 bg-paper-warm/30">
                <p className="font-serif italic text-xs text-ink-muted tracking-wide">Deck de Estudo</p>
                <h3 className="kd-heading mt-2 text-2xl tracking-tight">Limpar deck?</h3>
              </div>
              <div className="p-8">
                <p className="text-sm text-ink-muted leading-relaxed">
                  Isso irá remover {cards.length} {cards.length === 1 ? "card" : "cards"} do seu deck. Esta ação não pode ser desfeita.
                </p>
              </div>
              <div className="px-8 pb-8 flex gap-3">
                <button
                  onClick={() => setShowConfirmClear(false)}
                  className="kd-btn-ghost flex-1 justify-center focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => {
                    clearCards();
                    setShowConfirmClear(false);
                  }}
                  className="kd-btn flex-1 justify-center bg-vermilion text-paper border-vermilion hover:bg-vermilion-deep focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded"
                >
                  Limpar deck
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}
