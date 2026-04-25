import { type ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CapabilityKey } from "@/components/ShortcutBar";

interface CapabilityModalPlaceholderProps {
  capability: CapabilityKey | null;
  onOpenChange: (open: boolean) => void;
}

const META: Record<CapabilityKey, { title: string; description: string; step: string; mockBody: ReactNode }> = {
  mail: {
    title: "Mail — aralık seçimi",
    description: "Gmail özeti için tarih aralığı seç.",
    step: "Step 2",
    mockBody: (
      <div className="grid grid-cols-3 gap-2">
        {["Günlük", "Haftalık", "Özel"].map((label) => (
          <div
            key={label}
            className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-4 text-center text-sm text-slate-300"
          >
            {label}
          </div>
        ))}
      </div>
    ),
  },
  translation: {
    title: "Çeviri",
    description: "Metni yapıştır, kaynak ve hedef dili seç.",
    step: "Step 3",
    mockBody: (
      <div className="space-y-3">
        <div className="h-20 rounded-lg border border-slate-700 bg-slate-900/60 p-2 text-xs text-slate-500">
          (kaynak metin)
        </div>
        <div className="h-20 rounded-lg border border-slate-700 bg-slate-900/60 p-2 text-xs text-slate-500">
          (çeviri)
        </div>
      </div>
    ),
  },
  calendar: {
    title: "Takvim — etkinlik oluştur",
    description: "Başlık, tarih, saat ve detay gir.",
    step: "Step 4",
    mockBody: (
      <div className="space-y-2">
        {["Başlık", "Tarih", "Saat", "Detay"].map((field) => (
          <div
            key={field}
            className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-500"
          >
            {field} (placeholder)
          </div>
        ))}
      </div>
    ),
  },
  document: {
    title: "Döküman — yükle veya Drive seç",
    description: "PDF/TXT yükle veya Drive'dan seç.",
    step: "Step 5",
    mockBody: (
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-dashed border-slate-600 bg-slate-900/40 px-3 py-6 text-center text-xs text-slate-500">
          Drive'dan seç
        </div>
        <div className="rounded-lg border border-dashed border-slate-600 bg-slate-900/40 px-3 py-6 text-center text-xs text-slate-500">
          Upload
        </div>
      </div>
    ),
  },
};

export function CapabilityModalPlaceholder({
  capability,
  onOpenChange,
}: CapabilityModalPlaceholderProps) {
  const meta = capability ? META[capability] : null;

  return (
    <Dialog open={capability !== null} onOpenChange={onOpenChange}>
      {meta && (
        <DialogContent data-testid={`modal-${capability}`}>
          <DialogHeader>
            <DialogTitle>{meta.title}</DialogTitle>
            <DialogDescription>{meta.description}</DialogDescription>
          </DialogHeader>
          <div className="mt-4">{meta.mockBody}</div>
          <p className="mt-5 text-xs text-slate-500">
            Bu özellik henüz aktif değil — {meta.step}'te gelecek.
          </p>
        </DialogContent>
      )}
    </Dialog>
  );
}
