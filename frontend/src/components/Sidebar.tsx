import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useStore } from "../store";
import { pageImageUrl } from "../api";

export function Sidebar() {
  const sessionId = useStore((s) => s.sessionId);
  const totalPages = useStore((s) => s.totalPages);
  const currentPage = useStore((s) => s.currentPage);
  const setCurrentPage = useStore((s) => s.setCurrentPage);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  useEffect(() => {
    const el = itemRefs.current[currentPage];
    if (el && listRef.current) {
      const list = listRef.current;
      const elTop = el.offsetTop;
      const elBottom = elTop + el.offsetHeight;
      const viewTop = list.scrollTop;
      const viewBottom = viewTop + list.clientHeight;
      if (elTop < viewTop || elBottom > viewBottom) {
        list.scrollTo({ top: elTop - list.clientHeight / 2 + el.offsetHeight / 2, behavior: "smooth" });
      }
    }
  }, [currentPage]);

  if (!sessionId) return null;

  return (
    <aside className="w-[140px] shrink-0 h-full bg-paper-warm border-r border-ink/10 flex flex-col">
      <div className="px-3 py-3 border-b border-ink/10 flex items-center justify-between">
        <span className="kd-kicker">Páginas</span>
        <span className="font-mono text-[10px] text-ink-muted">
          {currentPage}/{totalPages}
        </span>
      </div>
      <div ref={listRef} className="flex-1 overflow-y-auto px-2 py-2 space-y-2">
        {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => {
          const active = n === currentPage;
          return (
            <button
              key={n}
              ref={(el) => {
                itemRefs.current[n] = el;
              }}
              onClick={() => setCurrentPage(n)}
              className={[
                "relative w-full block border transition-colors",
                active
                  ? "border-ink ring-1 ring-ink/20"
                  : "border-ink/10 hover:border-ink/40",
                "focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
              ].join(" ")}
            >
              <div className="relative aspect-[2/3] bg-paper overflow-hidden">
                <img
                  src={pageImageUrl(sessionId, n, 160)}
                  alt={`Página ${n}`}
                  loading="lazy"
                  className="absolute inset-0 w-full h-full object-cover"
                />
                {active && (
                  <motion.div
                    layoutId="page-active-bar"
                    className="absolute top-0 left-0 bottom-0 w-[3px] bg-vermilion"
                  />
                )}
              </div>
              <div className="px-1.5 py-1 flex items-center justify-between">
                <span className="font-mono text-[10px] text-ink-muted">
                  {String(n).padStart(2, "0")}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
