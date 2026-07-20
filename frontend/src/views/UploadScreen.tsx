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
    <div className="min-h-full flex flex-col bg-paper relative overflow-hidden">
      {/* Massive 読 kanji as background element */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 0.04, scale: 1 }}
        transition={{ duration: 2, ease: [0.2, 0.7, 0.1, 1] }}
        className="absolute inset-0 flex items-center justify-center pointer-events-none select-none"
        aria-hidden="true"
      >
        <span
          className="font-serif font-bold text-ink"
          style={{ fontSize: "min(80vw, 80vh)", lineHeight: 1 }}
        >
          読
        </span>
      </motion.div>

      <div className="relative z-10 flex-1 flex flex-col justify-center px-8 md:px-16 lg:px-24 py-16">
        <div className="max-w-6xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left column: editorial copy */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, ease: [0.2, 0.7, 0.1, 1], delay: 0.5 }}
            className="flex flex-col"
          >
            <YomiLogo size={48} />

            <div className="mt-6 flex items-center gap-2">
              <span className="font-serif italic text-sm text-ink-muted">読み</span>
              <span className="font-serif italic text-sm text-vermilion">·</span>
              <span className="font-serif italic text-sm text-ink-muted">YOMI</span>
            </div>

            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.6, ease: [0.2, 0.7, 0.1, 1] }}
              className="kd-heading mt-8 text-5xl md:text-6xl lg:text-7xl leading-[0.95] tracking-tight"
            >
              Leia mangá
              <br />
              sem dicionário.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9, duration: 0.6 }}
              className="mt-6 text-ink-muted text-base md:text-lg max-w-md leading-relaxed"
            >
              Passe o mouse sobre qualquer balão e descubra o significado
              instantaneamente. Sem pausas, sem dicionário. Clique para salvar
              e estudar depois.
            </motion.p>
          </motion.div>

          {/* Right column: dropzone + steps */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, ease: [0.2, 0.7, 0.1, 1], delay: 0.6 }}
            className="flex flex-col"
          >
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
                "w-full cursor-pointer border-2 border-dashed",
                "transition-all duration-300 ease-out",
                isOver
                  ? "border-vermilion bg-vermilion/[0.05] scale-[1.01]"
                  : "border-ink/30 hover:border-ink/70 hover:bg-paper-warm",
                "p-12 flex flex-col items-center gap-5",
                "focus:outline-none focus:ring-2 focus:ring-vermilion/50 rounded",
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
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex flex-col items-center gap-4"
                  >
                    <div className="h-10 w-10 border-2 border-vermilion border-t-transparent rounded-full animate-spin" />
                    <p className="font-serif italic text-sm text-ink-muted">
                      Preparando seu mangá…
                    </p>
                  </motion.div>
                ) : picked ? (
                  <motion.div
                    key="picked"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center gap-4"
                  >
                    <FileArchive className="h-10 w-10 text-vermilion" />
                    <p className="font-mono text-sm text-ink">{picked.name}</p>
                  </motion.div>
                ) : (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex flex-col items-center gap-4"
                  >
                    <UploadCloud className="h-12 w-12 text-ink-muted" />
                    <p className="font-serif italic text-base text-ink">
                      Arraste seu mangá aqui
                    </p>
                    <p className="text-ink-muted text-sm">ou clique para selecionar</p>
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

            {/* Steps: horizontal on desktop, vertical on mobile */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8, duration: 0.5 }}
              className="mt-8 grid grid-cols-3 gap-6"
            >
              {[
                { k: "01", t: "Abra seu mangá", d: "Navegue pelas páginas com zoom e pan." },
                { k: "02", t: "Passe o mouse", d: "Descubra o significado de cada balão." },
                { k: "03", t: "Clique para salvar", d: "Transforme em cards de estudo." },
              ].map((s) => (
                <div key={s.k} className="border-t border-ink/15 pt-3">
                  <p className="font-mono text-[10px] text-ink-muted tracking-wider">
                    {s.k}
                  </p>
                  <p className="mt-1.5 text-xs font-semibold text-ink">{s.t}</p>
                  <p className="mt-1 text-[11px] text-ink-muted leading-relaxed">
                    {s.d}
                  </p>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </div>

      <footer className="relative z-10 px-8 md:px-16 lg:px-24 py-6 border-t border-ink/10">
        <p className="font-serif italic text-xs text-ink-muted/60">
          Projeto final · Processamento Digital de Imagens · UFU
        </p>
      </footer>
    </div>
  );
}
