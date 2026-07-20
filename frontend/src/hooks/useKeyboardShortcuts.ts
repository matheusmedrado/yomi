import { useEffect } from "react";
import { useStore } from "../store";

export function useKeyboardShortcuts() {
  const currentPage = useStore((s) => s.currentPage);
  const totalPages = useStore((s) => s.totalPages);
  const setCurrentPage = useStore((s) => s.setCurrentPage);
  const toggleShowAllBoxes = useStore((s) => s.toggleShowAllBoxes);
  const toggleFocusMode = useStore((s) => s.toggleFocusMode);
  const debugStage = useStore((s) => s.debugStage);
  const view = useStore((s) => s.view);
  const activeCardId = useStore((s) => s.activeCardId);
  const setActiveCardId = useStore((s) => s.setActiveCardId);

  useEffect(() => {
    if (view !== "reader") return;
    const onKey = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.key === "Escape") {
        if (activeCardId) {
          setActiveCardId(null);
          return;
        }
      }

      const zoom = (detail: string) =>
        window.dispatchEvent(new CustomEvent("yomi:zoom", { detail }));

      switch (e.key) {
        case "ArrowLeft":
          setCurrentPage(Math.max(1, currentPage - 1));
          break;
        case "ArrowRight":
          setCurrentPage(Math.min(totalPages, currentPage + 1));
          break;
        case "+":
        case "=":
          zoom("in");
          break;
        case "-":
        case "_":
          zoom("out");
          break;
        case "0":
          zoom("reset");
          break;
        case "b":
          toggleShowAllBoxes();
          break;
        case "f":
          toggleFocusMode();
          break;
        case "d": {
          const order: (typeof debugStage)[] = [
            "otsu",
            "mask",
            "cc",
            "watershed",
            null,
          ];
          const idx = debugStage ? order.indexOf(debugStage) : -1;
          const next = order[(idx + 1) % order.length];
          useStore.setState({ debugStage: next });
          break;
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    view,
    currentPage,
    totalPages,
    setCurrentPage,
    toggleShowAllBoxes,
    toggleFocusMode,
    debugStage,
    activeCardId,
    setActiveCardId,
  ]);
}
