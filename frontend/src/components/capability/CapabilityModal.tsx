import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CapabilityKey } from "@/components/ShortcutBar";

import { CalendarForm, type CalendarDraft } from "./CalendarForm";
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
    title: "Mail — günlük özet (mock)",
    description: "Kategori kategori ayrılmış son mailler. Step 2'de gerçek Gmail verisi.",
  },
  translation: {
    title: "Çeviri (mock)",
    description: "Kaynak dili ve hedef dili seç. Step 3'te Gemini ile çalışacak.",
  },
  calendar: {
    title: "Takvim (mock)",
    description: "Etkinlik oluştur veya yaklaşan etkinlikleri gör. Step 4'te Google Calendar.",
  },
  document: {
    title: "Döküman (mock)",
    description: "Drive'dan seç veya PDF/TXT yükle. Step 5'te parse + Q&A.",
  },
};

export function CapabilityModal({ capability, onOpenChange }: CapabilityModalProps) {
  const meta = capability ? META[capability] : null;

  const handleCalendarSubmit = (draft: CalendarDraft) => {
    toast.info("Takvim CRUD Step 4'te devreye girecek.", { duration: 2500 });
    onOpenChange(false);
    void draft;
  };

  const handleMailReply = () => {
    toast.info("Batch reply akışı Step 2.7'de gelecek.", { duration: 2500 });
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
                <CalendarForm onSubmit={handleCalendarSubmit} />
                <div>
                  <h3 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                    Yaklaşan etkinlikler
                  </h3>
                  <EventList />
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
