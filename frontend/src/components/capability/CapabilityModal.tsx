import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CapabilityKey } from "@/components/ShortcutBar";

import { CalendarForm } from "./CalendarForm";
import { DocumentCard } from "./DocumentCard";
import { EventList } from "./EventList";
import { MailCard } from "./MailCard";
import { TranslationCard } from "./TranslationCard";

interface CapabilityModalProps {
  capability: CapabilityKey | null;
  onOpenChange: (open: boolean) => void;
}

const META: Record<CapabilityKey, { title: string; description: string }> = {
  mail: {
    title: "Mail — günlük özet",
    description: "Kategori kategori ayrılmış son mailler.",
  },
  translation: {
    title: "Çeviri",
    description: "Kaynak dili ve hedef dili seç, metni yapıştır, Gemini çevirir.",
  },
  calendar: {
    title: "Takvim",
    description: "Etkinlik oluştur veya 7 günlük ajandayı gör.",
  },
  document: {
    title: "Döküman",
    description: "Drive'dan seç veya PDF/TXT yükle, belgeden soru sor.",
  },
};

export function CapabilityModal({ capability, onOpenChange }: CapabilityModalProps) {
  const meta = capability ? META[capability] : null;
  const [calendarReloadKey, setCalendarReloadKey] = useState(0);

  const handleMailReply = () => {
    // MailCard switches to its inline BatchReplyView; nothing to do here.
  };

  const handleEventCreated = () => {
    setCalendarReloadKey((k) => k + 1);
  };

  return (
    <Dialog open={capability !== null} onOpenChange={onOpenChange}>
      {meta && capability && (
        <DialogContent
          data-testid={`modal-${capability}`}
          className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"
        >
          <DialogHeader>
            <DialogTitle>{meta.title}</DialogTitle>
            <DialogDescription>{meta.description}</DialogDescription>
          </DialogHeader>

          <div className="mt-4">
            {capability === "mail" && <MailCard onReplyClick={handleMailReply} />}
            {capability === "translation" && <TranslationCard />}
            {capability === "calendar" && (
              <div className="space-y-5">
                <CalendarForm onCreated={handleEventCreated} />
                <div>
                  <h3 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                    Yaklaşan etkinlikler
                  </h3>
                  <EventList reloadKey={calendarReloadKey} />
                </div>
              </div>
            )}
            {capability === "document" && <DocumentCard />}
          </div>
        </DialogContent>
      )}
    </Dialog>
  );
}
