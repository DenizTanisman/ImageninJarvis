import {
  FileText,
  HardDriveUpload,
  Loader2,
  RotateCcw,
  Send,
  Upload,
} from "lucide-react";
import { useEffect, useState, type ChangeEvent, type DragEvent } from "react";

import {
  askDocument,
  ChatNetworkError,
  googleConnectUrl,
  importDriveFile,
  listDriveFiles,
  uploadDocument,
  type DriveFileDTO,
  type UploadedDocDTO,
} from "@/api/client";
import { cn } from "@/lib/utils";
import { useDocumentContext } from "@/store/document";

type Tab = "drive" | "upload";

type Phase =
  | { kind: "pick" }
  | { kind: "ingesting"; source: "drive" | "upload" }
  | { kind: "ready"; doc: UploadedDocDTO }
  | { kind: "error"; message: string };

export function DocumentCard() {
  const [tab, setTab] = useState<Tab>("upload");
  const [phase, setPhase] = useState<Phase>({ kind: "pick" });
  const setActiveDoc = useDocumentContext((s) => s.setActiveDoc);
  const clearActiveDoc = useDocumentContext((s) => s.clearActiveDoc);

  const reset = () => {
    clearActiveDoc();
    setPhase({ kind: "pick" });
  };

  const finishIngest = (doc: UploadedDocDTO) => {
    setActiveDoc(doc);
    setPhase({ kind: "ready", doc });
  };

  if (phase.kind === "ready") {
    return <ReadyState doc={phase.doc} onReset={reset} />;
  }

  return (
    <div data-testid="document-card" className="space-y-3">
      <div className="flex rounded-lg bg-slate-900/70 p-1">
        <TabButton
          active={tab === "upload"}
          onClick={() => setTab("upload")}
          testId="tab-upload"
        >
          <Upload className="h-4 w-4" />
          Upload
        </TabButton>
        <TabButton
          active={tab === "drive"}
          onClick={() => setTab("drive")}
          testId="tab-drive"
        >
          <HardDriveUpload className="h-4 w-4" />
          Drive'dan seç
        </TabButton>
      </div>

      {phase.kind === "ingesting" && (
        <div
          data-testid="doc-ingesting"
          className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-8 text-sm text-slate-400"
        >
          <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
          {phase.source === "upload" ? "Yükleniyor…" : "Drive'dan getiriliyor…"}
        </div>
      )}

      {phase.kind === "error" && (
        <div
          data-testid="doc-error"
          className="space-y-3 rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100"
        >
          <p>{phase.message}</p>
          <button
            type="button"
            onClick={reset}
            className="rounded bg-slate-800 px-3 py-1 text-xs text-slate-200"
          >
            Tekrar dene
          </button>
        </div>
      )}

      {phase.kind !== "ingesting" && phase.kind !== "error" && tab === "upload" && (
        <UploadZone
          onSelected={(file) => {
            setPhase({ kind: "ingesting", source: "upload" });
            uploadDocument(file)
              .then(finishIngest)
              .catch((err) => {
                const message =
                  err instanceof ChatNetworkError ? err.message : "Beklenmeyen hata.";
                setPhase({ kind: "error", message });
              });
          }}
        />
      )}

      {phase.kind !== "ingesting" && phase.kind !== "error" && tab === "drive" && (
        <DrivePicker
          onPicked={(fileId) => {
            setPhase({ kind: "ingesting", source: "drive" });
            importDriveFile(fileId)
              .then(finishIngest)
              .catch((err) => {
                const message =
                  err instanceof ChatNetworkError ? err.message : "Beklenmeyen hata.";
                setPhase({ kind: "error", message });
              });
          }}
        />
      )}
    </div>
  );
}

interface UploadZoneProps {
  onSelected: (file: File) => void;
}

function UploadZone({ onSelected }: UploadZoneProps) {
  const [hover, setHover] = useState(false);

  const handleFile = (file: File | null | undefined) => {
    if (!file) return;
    onSelected(file);
  };

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setHover(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0]);
  };

  return (
    <label
      data-testid="upload-zone"
      onDragOver={(e) => {
        e.preventDefault();
        setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={onDrop}
      className={cn(
        "block cursor-pointer rounded-xl border-2 border-dashed p-6 text-center text-sm transition",
        hover
          ? "border-sky-400 bg-sky-500/10 text-sky-100"
          : "border-slate-700 bg-slate-900/30 text-slate-400 hover:border-slate-600",
      )}
    >
      <Upload className="mx-auto mb-2 h-6 w-6 text-sky-300" />
      Dosyayı buraya sürükle ya da tıkla.
      <div className="mt-1 text-xs text-slate-500">
        Desteklenen: .pdf, .txt · Max 10 MB
      </div>
      <input
        data-testid="upload-input"
        type="file"
        accept=".pdf,.txt,application/pdf,text/plain"
        className="hidden"
        onChange={onChange}
      />
    </label>
  );
}

interface DrivePickerProps {
  onPicked: (fileId: string) => void;
}

type DriveLoad =
  | { kind: "loading" }
  | { kind: "ready"; files: DriveFileDTO[] }
  | { kind: "needs-auth" }
  | { kind: "error"; message: string };

function DrivePicker({ onPicked }: DrivePickerProps) {
  const [state, setState] = useState<DriveLoad>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    setState({ kind: "loading" });
    listDriveFiles(controller.signal)
      .then((files) => {
        if (!cancelled) setState({ kind: "ready", files });
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ChatNetworkError && /bağlı/i.test(err.message)) {
          setState({ kind: "needs-auth" });
        } else {
          setState({
            kind: "error",
            message: err instanceof ChatNetworkError ? err.message : "Beklenmeyen hata.",
          });
        }
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <div
        data-testid="drive-loading"
        className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-6 text-sm text-slate-400"
      >
        <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
        Drive listesi yükleniyor…
      </div>
    );
  }

  if (state.kind === "needs-auth") {
    return (
      <div
        data-testid="drive-needs-auth"
        className="space-y-3 rounded-xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100"
      >
        <p>Drive izni yok. Tekrar bağlanıp Drive iznini de ver.</p>
        <a
          href={googleConnectUrl()}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="drive-reconnect"
          className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-sky-400"
        >
          Tekrar Google'a bağlan
        </a>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div
        data-testid="drive-error"
        className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100"
      >
        {state.message}
      </div>
    );
  }

  if (state.files.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
        Drive'da PDF veya metin dosyası yok.
      </div>
    );
  }

  return (
    <ul data-testid="drive-list" className="space-y-1.5">
      {state.files.map((file) => (
        <li key={file.id}>
          <button
            type="button"
            data-testid={`drive-pick-${file.id}`}
            onClick={() => onPicked(file.id)}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-left text-sm text-slate-200 transition hover:border-sky-400 hover:bg-slate-800"
          >
            <div className="flex min-w-0 items-center gap-2">
              <FileText className="h-4 w-4 text-sky-300" />
              <span className="truncate">{file.name}</span>
            </div>
            <span className="shrink-0 text-xs text-slate-500">
              {file.mime_type === "application/pdf" ? "PDF" : "TXT"}
              {file.size_bytes > 0 && ` · ${formatSize(file.size_bytes)}`}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

interface ReadyStateProps {
  doc: UploadedDocDTO;
  onReset: () => void;
}

interface QAItem {
  question: string;
  answer: string;
}

function ReadyState({ doc, onReset }: ReadyStateProps) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<QAItem[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    const q = question.trim();
    if (!q) return;
    setPending(true);
    setError(null);
    try {
      const response = await askDocument({ doc_id: doc.doc_id, question: q });
      if (response.ok) {
        setHistory((prev) => [
          ...prev,
          { question: q, answer: response.data.answer },
        ]);
        setQuestion("");
      } else {
        setError(response.error.user_message);
      }
    } catch (err) {
      setError(err instanceof ChatNetworkError ? err.message : "Beklenmeyen hata.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div data-testid="document-ready" className="space-y-3">
      <div className="flex items-center justify-between gap-3 rounded-xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-100">
        <div className="flex min-w-0 items-center gap-2">
          <FileText className="h-4 w-4 shrink-0" />
          <span className="truncate font-medium">{doc.original_name}</span>
          <span className="shrink-0 text-xs text-emerald-200/80">
            · {doc.page_count} sayfa · {formatSize(doc.size_bytes)}
          </span>
        </div>
        <button
          type="button"
          onClick={onReset}
          data-testid="doc-reset"
          className="flex shrink-0 items-center gap-1 rounded px-2 py-1 text-xs text-slate-300 transition hover:text-slate-100"
        >
          <RotateCcw className="h-3 w-3" />
          Başka belge
        </button>
      </div>

      <ul className="space-y-2" data-testid="qa-history">
        {history.map((item, index) => (
          <li
            key={index}
            className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-sm"
          >
            <div className="text-xs uppercase tracking-wide text-slate-500">
              Soru
            </div>
            <div className="text-slate-200">{item.question}</div>
            <div className="mt-2 text-xs uppercase tracking-wide text-slate-500">
              Cevap
            </div>
            <div className="whitespace-pre-wrap text-slate-100">{item.answer}</div>
          </li>
        ))}
      </ul>

      {error && (
        <div
          data-testid="doc-error"
          className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-xs text-rose-100"
        >
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <input
          data-testid="qa-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask();
            }
          }}
          placeholder="Bu belge hakkında soru sor…"
          disabled={pending}
          className="flex-1 rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={ask}
          disabled={pending || !question.trim()}
          data-testid="qa-submit"
          className={cn(
            "flex items-center gap-2 rounded bg-sky-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500",
          )}
        >
          {pending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Sor
        </button>
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  testId: string;
  children: React.ReactNode;
}

function TabButton({ active, onClick, testId, children }: TabButtonProps) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-xs transition",
        active
          ? "bg-slate-800 text-sky-200 ring-1 ring-sky-400/50"
          : "text-slate-400 hover:text-slate-200",
      )}
    >
      {children}
    </button>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
