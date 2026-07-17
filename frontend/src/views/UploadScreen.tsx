import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileArchive, AlertCircle } from "lucide-react";
import { useStore } from "../store";
import { loadCbz } from "../api";
import { YomiLogo } from "../components/YomiLogo";

export function UploadScreen() {
  const setSession = useStore((s) => s.setSession);
  const setView = useStore((s) => s.setView);
  const uploading = useStore((s) => s.uploading);
  const uploadError = useStore((s) => s.uploadError);
  const setUploading = useStore((s) => s.setUploading);
  const setUploadError = useStore((s) => s.setUploadError);

  const [isOver, setIsOver] = useState(false);
  const [picked, setPicked] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setPicked(file);
      setUploadError(null);
      setUploading(true);
      try {
        const res = await loadCbz(file);
        setSession({
          sessionId: res.session_id,
          pages: res.pages,
          title: res.title,
        });
        setView("reader");
      } catch (e) {
        setUploadError(e instanceof Error ? e.message : String(e));
      } finally {
        setUploading(false);
      }
    },
    [setSession, setUploading, setUploadError, setView],
  );

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-6 py-12 bg-paper relative overflow-hidden">
      {/* Decorative gridlines, very faint, editorial */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #0a0a0a 1px, transparent 1px), linear-gradient(to bottom, #0a0a0a 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <motion.div
        initial={{ y: 12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.2, 0.7, 0.1, 1] }}
        className="relative z-10 flex flex-col items-center text-center max-w-2xl w-full"
      >
        <YomiLogo size={72} />

        <div className="mt-6 flex items-center gap-3">
          <span className="kd-kicker">Yomi — 読み</span>
          <span className="h-px w-8 bg-ink/30" />
          <span className="kd-kicker text-ink-muted/80">UFU · PDI</span>
        </div>

        <h1 className="kd-heading mt-4 text-5xl md:text-6xl">
          Read&nbsp;manga, hover, learn.
        </h1>
        <p className="mt-5 text-ink-muted text-base md:text-lg max-w-md leading-relaxed">
          A manga reader that detects speech bubbles with classical image
          processing and shows you the reading on hover. Drop a CBZ to begin.
        </p>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsOver(true);
          }}
          onDragLeave={() => setIsOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
          onClick={() => inputRef.current?.click()}
          className={[
            "mt-10 w-full max-w-xl cursor-pointer border border-dashed",
            "transition-all duration-200 ease-out",
            isOver
              ? "border-vermilion bg-vermilion/[0.04] scale-[1.01]"
              : "border-ink/30 hover:border-ink hover:bg-paper-warm",
            "p-12 flex flex-col items-center gap-4",
          ].join(" ")}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".cbz,.zip,application/zip,application/x-cbz-compressed"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          <AnimatePresence mode="wait">
            {uploading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-3"
              >
                <div className="h-8 w-8 border-2 border-ink border-t-transparent rounded-full animate-spin" />
                <p className="kd-kicker">Extracting pages…</p>
              </motion.div>
            ) : picked ? (
              <motion.div
                key="picked"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center gap-2"
              >
                <FileArchive className="h-8 w-8 text-ink" />
                <p className="font-mono text-sm">{picked.name}</p>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-3"
              >
                <UploadCloud className="h-10 w-10 text-ink" />
                <p className="kd-kicker">Drop a CBZ here</p>
                <p className="text-ink-muted text-sm">or click to browse</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {uploadError && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4 flex items-center gap-2 text-vermilion text-sm"
            >
              <AlertCircle className="h-4 w-4" />
              <span>{uploadError}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-12 grid grid-cols-3 gap-6 text-left max-w-xl w-full">
          {[
            {
              k: "01",
              t: "Open a page",
              d: "Pages render in the reader. Pan and zoom with the mouse.",
            },
            {
              k: "02",
              t: "Hover a bubble",
              d: "We detect the text region with Otsu, morphology, and watershed.",
            },
            {
              k: "03",
              t: "Read the reading",
              d: "Recognition and furigana show up next to the cursor.",
            },
          ].map((s) => (
            <div key={s.k} className="border-t border-ink/20 pt-3">
              <p className="font-mono text-[10px] text-ink-muted">{s.k}</p>
              <p className="mt-2 text-sm font-semibold">{s.t}</p>
              <p className="mt-1 text-xs text-ink-muted leading-relaxed">
                {s.d}
              </p>
            </div>
          ))}
        </div>
      </motion.div>

      <footer className="relative z-10 mt-16 kd-kicker text-ink-muted/70">
        Final project · Processamento Digital de Imagens · UFU
      </footer>
    </div>
  );
}
