import { FileText, HardDriveUpload, Upload } from "lucide-react";
import { useState } from "react";

import { MOCK_DRIVE_FILES } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Tab = "drive" | "upload";

export function DocumentCard() {
  const [tab, setTab] = useState<Tab>("drive");

  return (
    <div data-testid="document-card" className="space-y-3">
      <div className="flex rounded-lg bg-slate-900/70 p-1">
        <TabButton
          active={tab === "drive"}
          onClick={() => setTab("drive")}
          testId="tab-drive"
        >
          <HardDriveUpload className="h-4 w-4" />
          Drive'dan seç
        </TabButton>
        <TabButton
          active={tab === "upload"}
          onClick={() => setTab("upload")}
          testId="tab-upload"
        >
          <Upload className="h-4 w-4" />
          Upload
        </TabButton>
      </div>

      {tab === "drive" ? (
        <ul data-testid="drive-list" className="space-y-1.5">
          {MOCK_DRIVE_FILES.map((file) => (
            <li
              key={file.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-sm text-slate-200"
            >
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 text-sky-300" />
                <span className="truncate">{file.name}</span>
              </div>
              <span className="shrink-0 text-xs text-slate-500">
                {file.mimeType === "application/pdf" ? "PDF" : "TXT"} · {file.size}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <div
          data-testid="upload-zone"
          className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/30 p-6 text-center text-sm text-slate-400"
        >
          <Upload className="mx-auto mb-2 h-6 w-6 text-sky-300" />
          Dosyayı buraya sürükle ya da tıkla.
          <div className="mt-1 text-xs text-slate-500">
            Desteklenen: .pdf, .txt · Max 10 MB
          </div>
        </div>
      )}
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
