import { CalendarDays, Clock, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  callCalendar,
  ChatNetworkError,
  type CalendarEventDTO,
} from "@/api/client";
import {
  ConfirmDeleteDialog,
  EditDialog,
} from "@/components/capability/EventList";
import { cn } from "@/lib/utils";

export type CalendarCardAction = "create" | "update" | "delete_proposal";

interface CalendarEventCardProps {
  event: CalendarEventDTO;
  /** Why this card is showing up in the chat:
   * - "create" / "update": confirms a successful write
   * - "delete_proposal": user typed "X'i sil" in chat; card asks them
   *   to confirm before actually deleting */
  action?: CalendarCardAction;
}

type Status = "active" | "deleted";

const BADGE_STYLES: Record<CalendarCardAction, { label: string; cls: string }> = {
  create: {
    label: "yeni etkinlik",
    cls: "bg-emerald-500/15 text-emerald-200",
  },
  update: {
    label: "güncellendi",
    cls: "bg-emerald-500/15 text-emerald-200",
  },
  delete_proposal: {
    label: "silmek üzeresin",
    cls: "bg-rose-500/15 text-rose-200",
  },
};

export function CalendarEventCard({ event: initial, action }: CalendarEventCardProps) {
  const [event, setEvent] = useState<CalendarEventDTO>(initial);
  const [status, setStatus] = useState<Status>("active");
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isDeleteProposal = action === "delete_proposal";

  const handleDelete = async () => {
    setConfirmDelete(false);
    try {
      const response = await callCalendar({
        action: "delete",
        event_id: event.id,
      });
      if (response.ok) {
        toast.success(`"${event.summary}" silindi.`, { duration: 2500 });
        setStatus("deleted");
      } else {
        toast.error(response.error.user_message, { duration: 3000 });
      }
    } catch (err) {
      toast.error(
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.",
        { duration: 3000 },
      );
    }
  };

  if (status === "deleted") {
    return (
      <div
        data-testid="calendar-event-card"
        className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-500"
      >
        Etkinlik silindi.
      </div>
    );
  }

  return (
    <div
      data-testid="calendar-event-card"
      className={cn(
        "rounded-xl border p-3",
        isDeleteProposal
          ? "border-rose-400/40 bg-rose-500/5"
          : "border-slate-800 bg-slate-900/50",
      )}
    >
      {action && (
        <div
          className={cn(
            "mb-2 inline-block rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide",
            BADGE_STYLES[action].cls,
          )}
        >
          {BADGE_STYLES[action].label}
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-100">
            {event.summary}
          </div>
          {event.description && (
            <div className="line-clamp-2 text-xs text-slate-400">
              {event.description}
            </div>
          )}
        </div>
        <div className="shrink-0 space-y-1 text-right text-xs text-slate-400">
          <div className="flex items-center justify-end gap-1">
            <CalendarDays className="h-3 w-3" />
            {event.start.slice(0, 10)}
          </div>
          <div className="flex items-center justify-end gap-1">
            <Clock className="h-3 w-3" />
            {event.start.slice(11, 16)} – {event.end.slice(11, 16)}
          </div>
        </div>
      </div>
      {isDeleteProposal && (
        <p className="mt-2 text-xs text-rose-200/90">
          Bu etkinliği silmek istediğine emin misin? Onaylarsan kalıcı olarak
          silinecek.
        </p>
      )}
      <div className="mt-2 flex justify-end gap-2">
        {!isDeleteProposal && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            data-testid="calendar-event-edit"
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-300 transition hover:bg-slate-800"
          >
            <Pencil className="h-3 w-3" />
            Düzenle
          </button>
        )}
        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          data-testid="calendar-event-delete"
          className={cn(
            "flex items-center gap-1 rounded px-2 py-1 text-xs transition",
            isDeleteProposal
              ? "bg-rose-500 text-white hover:bg-rose-400"
              : "text-rose-300 hover:bg-rose-500/10",
          )}
        >
          <Trash2 className="h-3 w-3" />
          Sil
        </button>
      </div>

      {editing && (
        <EditDialog
          event={event}
          onClose={() => setEditing(false)}
          onSaved={(updated) => {
            setEditing(false);
            if (updated) setEvent(updated);
          }}
        />
      )}
      {confirmDelete && (
        <ConfirmDeleteDialog
          event={event}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={() => void handleDelete()}
        />
      )}
    </div>
  );
}
