import { useStore } from "./store";
import { UploadScreen } from "./views/UploadScreen";
import { ReaderLayout } from "./views/ReaderLayout";

export default function App() {
  const view = useStore((s) => s.view);

  return (
    <div className="h-full">
      {view === "upload" ? <UploadScreen /> : <ReaderLayout />}
    </div>
  );
}
