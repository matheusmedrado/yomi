import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "./store";
import { UploadScreen } from "./views/UploadScreen";
import { ReaderLayout } from "./views/ReaderLayout";

export default function App() {
  const view = useStore((s) => s.view);

  return (
    <div className="h-full">
      <AnimatePresence mode="wait">
        {view === "upload" ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <UploadScreen />
          </motion.div>
        ) : (
          <motion.div
            key="reader"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <ReaderLayout />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
