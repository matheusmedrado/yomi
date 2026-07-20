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
    <div className="min-h-full flex flex-col items-center justify-center px-6 py-16 bg-paper relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
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
        className="relative z-10 flex flex-col items-center text-center max-w-3xl w-full"
      >
        <YomiLogo size={80} />

        <div className="mt-8 flex items-center gap-2">
          <span className="kd-kicker text-sm">読み</span>
          <span className="kd-kicker text-sm text-vermilion">·</span>
          <span className="kd-kicker text-sm">YOMI</span>
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="kd-heading mt-6 text-5xl md:text-6xl lg:text-7xl leading-tight"
        >
          <span className="whitespace-nowrap">Leia mangá em japonês.</span>
          <br />
          <span className="text-vermilion">Passe o mouse.</span> Aprenda.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35, duration: 0.5 }}
          className="mt-8 text-ink-muted text-lg md:text-xl max-w-2xl leading-relaxed"
        >
          Um leitor de mangá que detecta balões de fala com processamento
          clássico de imagens e mostra a leitura, tradução e análise dos kanjis
          ao passar o mouse. Clique para criar cards de estudo.
        </motion.p>

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
            "mt-12 w-full max-w-2xl cursor-pointer border border-dashed",
            "transition-all duration-200 ease-out",
            isOver
              ? "border-vermilion bg-vermilion/[0.04] scale-[1.01]"
              : "border-ink/30 hover:border-ink hover:bg-paper-warm",
            "p-16 flex flex-col items-center gap-5",
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
                <div className="h-10 w-10 border-2 border-ink border-t-transparent rounded-full animate-spin" />
                <p className="kd-kicker text-base">Extraindo páginas…</p>
              </motion.div>
            ) : picked ? (
              <motion.div
                key="picked"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center gap-3"
              >
                <FileArchive className="h-10 w-10 text-ink" />
                <p className="font-mono text-base">{picked.name}</p>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-4"
              >
                <UploadCloud className="h-12 w-12 text-ink" />
                <p className="kd-kicker text-lg">Solte um CBZ aqui</p>
                <p className="text-ink-muted text-base">ou clique para procurar</p>
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
              className="mt-6 flex items-center gap-2 text-vermilion text-base"
            >
              <AlertCircle className="h-5 w-5" />
              <span>{uploadError}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="mt-16 grid grid-cols-3 gap-10 text-left max-w-3xl w-full"
        >
          {[
            {
              k: "01",
              t: "Abra uma página",
              d: "Navegue pelas páginas do mangá com zoom e pan.",
            },
            {
              k: "02",
              t: "Passe o mouse",
              d: "Veja a leitura, tradução e análise dos kanjis em tempo real.",
            },
            {
              k: "03",
              t: "Clique para estudar",
              d: "Crie cards de estudo e exporte para o Anki.",
            },
          ].map((s, i) => (
            <motion.div
              key={s.k}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.1, duration: 0.4 }}
              className="border-t border-ink/20 pt-4"
            >
              <p className="font-mono text-xs text-ink-muted">{s.k}</p>
              <p className="mt-3 text-base font-semibold">{s.t}</p>
              <p className="mt-2 text-sm text-ink-muted leading-relaxed">
                {s.d}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      <footer className="relative z-10 mt-20 kd-kicker text-sm text-ink-muted/70">
        Projeto final · Processamento Digital de Imagens · UFU
      </footer>
    </div>
  );
}
