import { motion } from "framer-motion";
import { useState } from "react";
import { useStore } from "../store";
import { regionImageUrl } from "../api";
import { X, RotateCcw, Trash2 } from "lucide-react";

export function FlashcardModal() {
  const activeCardId = useStore((s) => s.activeCardId);
  const cards = useStore((s) => s.cards);
  const sessionId = useStore((s) => s.sessionId);
  const setActiveCardId = useStore((s) => s.setActiveCardId);
  const removeCard = useStore((s) => s.removeCard);

  const card = cards.find((c) => c.id === activeCardId);
  const [flipped, setFlipped] = useState(false);

  if (!card || !sessionId) return null;

  const handleFlip = () => setFlipped((f) => !f);
  const handleClose = () => {
    setActiveCardId(null);
    setFlipped(false);
  };
  const handleDelete = () => {
    removeCard(card.id);
    handleClose();
  };

  const idx = cards.findIndex((c) => c.id === card.id);
  const prev = idx < cards.length - 1 ? cards[idx + 1] : null;
  const next = idx > 0 ? cards[idx - 1] : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={handleClose}
      className="fixed inset-0 z-50 bg-ink/60 backdrop-blur-sm flex items-center justify-center p-6"
    >
      <motion.div
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative w-full max-w-lg"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="kd-kicker">
            Card {idx + 1} de {cards.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={handleDelete}
              className="kd-btn-ghost text-vermilion"
              title="Excluir card"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              onClick={handleClose}
              className="kd-btn-ghost"
              title="Fechar (Esc)"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div
          className="relative w-full"
          style={{ perspective: "1200px", minHeight: "420px" }}
          onClick={handleFlip}
        >
          <motion.div
            animate={{ rotateY: flipped ? 180 : 0 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            className="relative w-full h-full"
            style={{ transformStyle: "preserve-3d", minHeight: "420px" }}
          >
            {/* Front */}
            <div
              className="absolute inset-0 bg-paper border border-ink/20 shadow-editorial-lg flex flex-col"
              style={{ backfaceVisibility: "hidden" }}
            >
              <div className="flex-1 flex items-center justify-center p-6 bg-paper-warm">
                <img
                  src={regionImageUrl(sessionId, card.page, card.region_id)}
                  alt=""
                  className="max-h-[200px] max-w-full object-contain shadow-editorial"
                />
              </div>
              <div className="p-6 border-t border-ink/10">
                <p className="font-serif text-2xl text-center leading-relaxed">
                  {card.text}
                </p>
                <p className="text-center text-ink-muted text-sm mt-3">
                  Toque para virar
                </p>
              </div>
            </div>

            {/* Back */}
            <div
              className="absolute inset-0 bg-paper border border-ink/20 shadow-editorial-lg overflow-y-auto"
              style={{
                backfaceVisibility: "hidden",
                transform: "rotateY(180deg)",
              }}
            >
              <div className="p-6 space-y-4">
                <div>
                  <span className="kd-kicker">Frase</span>
                  <p className="font-serif text-xl mt-1">{card.text}</p>
                  {card.furigana && card.furigana !== card.text && (
                    <p className="font-serif text-sm text-ink-muted mt-0.5">
                      {card.furigana}
                    </p>
                  )}
                  {card.romaji && (
                    <p className="font-mono text-[11px] text-ink-muted/70 mt-0.5">
                      {card.romaji}
                    </p>
                  )}
                </div>

                {card.translation && (
                  <div className="border-t border-ink/10 pt-3">
                    <span className="kd-kicker">Tradução</span>
                    <p className="text-ink mt-1 italic">{card.translation}</p>
                  </div>
                )}

                {card.kanji && card.kanji.length > 0 && (
                  <div className="border-t border-ink/10 pt-3">
                    <span className="kd-kicker">Kanji</span>
                    <div className="mt-2 space-y-2">
                      {card.kanji.map((k) => (
                        <div
                          key={k.char}
                          className="flex gap-3 items-start text-sm"
                        >
                          <span className="font-serif text-2xl text-[#c8102e] leading-none mt-0.5">
                            {k.char}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-ink font-medium">
                              {k.meanings_pt.join(", ") ||
                                k.meanings_en.join(", ")}
                            </p>
                            <p className="text-ink-muted text-xs mt-0.5">
                              {k.kun.length > 0 && (
                                <span>kun: {k.kun.join(", ")} </span>
                              )}
                              {k.on.length > 0 && (
                                <span>on: {k.on.join(", ")}</span>
                              )}
                            </p>
                            <p className="text-ink-muted/60 text-[10px] mt-0.5">
                              {[
                                k.strokes > 0 && `${k.strokes} traços`,
                                k.grade > 0 && `grau ${k.grade}`,
                                k.jlpt > 0 && `JLPT N${k.jlpt}`,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {card.tokens && card.tokens.length > 0 && (
                  <div className="border-t border-ink/10 pt-3">
                    <span className="kd-kicker">Palavras</span>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {card.tokens.map((t, i) => (
                        <span
                          key={i}
                          className="inline-flex flex-col items-center px-2 py-1 bg-paper-warm border border-ink/10 text-xs"
                        >
                          <span className="font-serif">{t.surface}</span>
                          {t.furigana !== t.surface && (
                            <span className="text-ink-muted text-[10px]">
                              {t.furigana}
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </div>

        <div className="flex items-center justify-between mt-3">
          <button
            onClick={() => prev && setActiveCardId(prev.id)}
            disabled={!prev}
            className="kd-btn-ghost disabled:opacity-30"
          >
            ← Anterior
          </button>
          <button
            onClick={handleFlip}
            className="kd-btn-ghost"
            title="Virar (Espaço)"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <button
            onClick={() => next && setActiveCardId(next.id)}
            disabled={!next}
            className="kd-btn-ghost disabled:opacity-30"
          >
            Próximo →
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
