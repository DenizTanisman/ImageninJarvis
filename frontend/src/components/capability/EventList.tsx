import { CalendarDays, Clock, Loader2, Pencil, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  callCalendar,
  ChatNetworkError,
  googleConnectUrl,
  type CalendarEventDTO,
} from "@/api/client";
import { cn } from "@/lib/utils";

interface EventListProps {
  /** Bumping this number forces a reload — the parent uses it after a
   * successful create / update / delete to refresh the list. */
  reloadKey?: number;
  /** When supplied, EventList skips the initial fetch and renders these
   * events directly. Used by chat-rendered candidate lists (e.g. when
   * "X'i sil" matches multiple events). After a delete/update, the
   * component still calls the API and reflects the changes locally. */
  initialEvents?: CalendarEventDTO[];
  /** Headline shown above the list — typically "X için adaylar" when
   * rendering ambiguous delete candidates inline. */
  headline?: string;
}

type Status =
  | { kind: "loading" }
  | { kind: "ready"; events: CalendarEventDTO[] }
  | { kind: "error"; message: string }
  | { kind: "needs-auth"; message: string };

export function EventList({
  reloadKey = 0,
  initialEvents,
  headline,
}: EventListProps) {
  const [status, setStatus] = useState<Status>(() =>
    initialEvents
      ? { kind: "ready", events: initialEvents }
      : { kind: "loading" },
  );
  const [editing, setEditing] = useState<CalendarEventDTO | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<CalendarEventDTO | null>(
    null,
  );

  useEffect(() => {
    if (initialEvents) {
      // Inline render path: trust the data we were handed. After a
      // delete / update inside this card, the user can still refresh
      // via the standard UI; we don't auto-fetch a fuller list.
      setStatus({ kind: "ready", events: initialEvents });
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    setStatus({ kind: "loading" });
    callCalendar({ action: "list", days: 7 }, controller.signal)
      .then((response) => {
        if (cancelled) return;
        if (response.ok && response.ui_type === "EventList") {
          setStatus({ kind: "ready", events: response.data.events });
        } else if (!response.ok) {
          const msg = response.error.user_message;
          if (
            msg.toLowerCase().includes("bağlı değilsin") ||
            msg.toLowerCase().includes("takvim izni")
          ) {
            setStatus({ kind: "needs-auth", message: msg });
          } else {
            setStatus({ kind: "error", message: msg });
          }
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus({
          kind: "error",
          message:
            err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.",
        });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [reloadKey, initialEvents]);

  const refresh = () => {
    setStatus({ kind: "loading" });
    callCalendar({ action: "list", days: 7 })
      .then((response) => {
        if (response.ok && response.ui_type === "EventList") {
          setStatus({ kind: "ready", events: response.data.events });
        }
      })
      .catch(() => {
        /* leave previous state */
      });
  };

  const removeLocal = (id: string) =>
    setStatus((prev) =>
      prev.kind === "ready"
        ? { kind: "ready", events: prev.events.filter((e) => e.id !== id) }
        : prev,
    );

  const replaceLocal = (updated: CalendarEventDTO) =>
    setStatus((prev) =>
      prev.kind === "ready"
        ? {
            kind: "ready",
            events: prev.events.map((e) => (e.id === updated.id ? updated : e)),
          }
        : prev,
    );

  const handleDelete = async (event: CalendarEventDTO) => {
    setConfirmDelete(null);
    try {
      const response = await callCalendar({
        action: "delete",
        event_id: event.id,
      });
      if (response.ok) {
        toast.success(`"${event.summary}" silindi.`, { duration: 2500 });
        // Inline (chat-rendered) mode: keep the curated list, just drop
        // the deleted row. Standalone mode: refetch so any server-side
        // changes since mount surface too.
        if (initialEvents) {
          removeLocal(event.id);
        } else {
          refresh();
        }
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

  if (status.kind === "loading") {
    return (
      <div
        data-testid="events-loading"
        className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-8 text-sm text-slate-400"
      >
        <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
        Etkinlikler yükleniyor…
      </div>
    );
  }

  if (status.kind === "needs-auth") {
    return (
      <div
        data-testid="events-needs-auth"
        className="space-y-3 rounded-xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100"
      >
        <p>{status.message}</p>
        <a
          href={googleConnectUrl()}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="events-reconnect"
          className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-sky-400"
        >
          Tekrar Google'a bağlan
        </a>
      </div>
    );
  }

  if (status.kind === "error") {
    return (
      <div
        data-testid="events-error"
        className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100"
      >
        {status.message}
      </div>
    );
  }

  if (status.events.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
        {initialEvents ? "Liste boşaldı." : "Önümüzdeki 7 günde etkinlik yok."}
      </div>
    );
  }

  return (
    <>
      {headline && (
        <p
          data-testid="event-list-headline"
          className="mb-2 text-xs text-slate-400"
        >
          {headline}
        </p>
      )}
      <ul data-testid="event-list" className="space-y-2">
        {status.events.map((event) => (
          <li
            key={event.id}
            data-testid={`event-${event.id}`}
            className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-slate-100">
                  {event.summary}
                </div>
                <div className="line-clamp-2 text-xs text-slate-400">
                  {event.description}
                </div>
              </div>
              <div className="shrink-0 space-y-1 text-right text-xs text-slate-400">
                <div className="flex items-center justify-end gap-1">
                  <CalendarDays className="h-3 w-3" />
                  {formatDate(event.start)}
                </div>
                <div className="flex items-center justify-end gap-1">
                  <Clock className="h-3 w-3" />
                  {formatTimeRange(event.start, event.end)}
                </div>
              </div>
            </div>
            <div className="mt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditing(event)}
                data-testid={`event-edit-${event.id}`}
                className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-300 transition hover:bg-slate-800"
              >
                <Pencil className="h-3 w-3" />
                Düzenle
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(event)}
                data-testid={`event-delete-${event.id}`}
                className="flex items-center gap-1 rounded px-2 py-1 text-xs text-rose-300 transition hover:bg-rose-500/10"
              >
                <Trash2 className="h-3 w-3" />
                Sil
              </button>
            </div>
          </li>
        ))}
      </ul>

      {editing && (
        <EditDialog
          event={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setEditing(null);
            if (initialEvents && updated) {
              replaceLocal(updated);
            } else {
              refresh();
            }
          }}
        />
      )}
      {confirmDelete && (
        <ConfirmDeleteDialog
          event={confirmDelete}
          onCancel={() => setConfirmDelete(null)}
          onConfirm={() => void handleDelete(confirmDelete)}
        />
      )}
    </>
  );
}

export interface EditDialogProps {
  event: CalendarEventDTO;
  onClose: () => void;
  onSaved: (updated?: CalendarEventDTO) => void;
}

export function EditDialog({ event, onClose, onSaved }: EditDialogProps) {
  const [summary, setSummary] = useState(event.summary);
  const [description, setDescription] = useState(event.description);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!summary.trim()) {
      setError("Başlık boş olamaz.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const response = await callCalendar({
        action: "update",
        event_id: event.id,
        summary: summary.trim(),
        description: description.trim(),
      });
      if (response.ok) {
        toast.success("Etkinlik güncellendi.", { duration: 2500 });
        onSaved(
          response.ui_type === "CalendarEvent" ? response.data : undefined,
        );
      } else {
        setError(response.error.user_message);
      }
    } catch (err) {
      setError(
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell title={`"${event.summary}"`} onClose={onClose} testId="event-edit-modal">
      <div className="space-y-3">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Başlık
          <input
            data-testid="edit-title"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Detay
          <textarea
            data-testid="edit-detail"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="resize-none rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400"
          />
        </label>
        {error && (
          <div className="rounded-md border border-rose-400/40 bg-rose-500/10 p-2 text-xs text-rose-100">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1 text-xs text-slate-300 hover:text-slate-100"
          >
            İptal
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            data-testid="edit-save"
            className={cn(
              "flex items-center gap-2 rounded bg-sky-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-sky-400",
              saving && "cursor-not-allowed bg-slate-800 text-slate-400",
            )}
          >
            {saving && <Loader2 className="h-3 w-3 animate-spin" />}
            Kaydet
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

export interface ConfirmDeleteDialogProps {
  event: CalendarEventDTO;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDeleteDialog({
  event,
  onCancel,
  onConfirm,
}: ConfirmDeleteDialogProps) {
  return (
    <ModalShell
      title="Etkinliği sil?"
      onClose={onCancel}
      testId="event-confirm-delete"
    >
      <p className="text-sm text-slate-200">
        <span className="font-semibold text-slate-50">{event.summary}</span>{" "}
        etkinliğini silmek istediğine emin misin? Bu işlem geri alınamaz.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          data-testid="event-confirm-cancel"
          className="rounded px-3 py-1 text-xs text-slate-300 hover:text-slate-100"
        >
          İptal
        </button>
        <button
          type="button"
          onClick={onConfirm}
          data-testid="event-confirm-yes"
          className="rounded bg-rose-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-400"
        >
          Evet, sil
        </button>
      </div>
    </ModalShell>
  );
}

interface ModalShellProps {
  title: string;
  onClose: () => void;
  testId: string;
  children: React.ReactNode;
}

function ModalShell({ title, onClose, testId, children }: ModalShellProps) {
  return (
    <div
      data-testid={testId}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
        <div className="mb-3 text-sm font-semibold text-slate-100">{title}</div>
        {children}
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  if (!iso) return "";
  // Strip off the time so the user sees "2026-04-28" not the ISO blob.
  return iso.slice(0, 10);
}

function formatTimeRange(startIso: string, endIso: string): string {
  const start = startIso.slice(11, 16);
  const end = endIso.slice(11, 16);
  return start && end ? `${start} – ${end}` : start || end || "";
}
