import { Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import {
  callCalendar,
  ChatNetworkError,
  type CalendarEventDTO,
} from "@/api/client";
import { cn } from "@/lib/utils";

interface CalendarFormProps {
  /** Optional callback fired after a successful create — parent can refresh
   * the list without round-tripping through the modal close/open cycle. */
  onCreated?: (event: CalendarEventDTO) => void;
}

export interface CalendarDraft {
  title: string;
  date: string;
  startTime: string;
  endTime: string;
  detail: string;
}

const EMPTY: CalendarDraft = {
  title: "",
  date: "",
  startTime: "",
  endTime: "",
  detail: "",
};

const ISTANBUL_OFFSET = "+03:00";

function buildIso(date: string, time: string): string {
  // "2026-04-28" + "14:00" → "2026-04-28T14:00:00+03:00"
  return `${date}T${time}:00${ISTANBUL_OFFSET}`;
}

export function CalendarForm({ onCreated }: CalendarFormProps) {
  const [draft, setDraft] = useState<CalendarDraft>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (field: keyof CalendarDraft, value: string) =>
    setDraft((prev) => ({ ...prev, [field]: value }));

  const valid =
    draft.title.trim().length > 0 &&
    draft.date.trim().length > 0 &&
    draft.startTime.trim().length > 0 &&
    draft.endTime.trim().length > 0 &&
    draft.startTime < draft.endTime;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await callCalendar({
        action: "create",
        summary: draft.title.trim(),
        start: buildIso(draft.date, draft.startTime),
        end: buildIso(draft.date, draft.endTime),
        description: draft.detail.trim(),
      });
      if (response.ok && response.ui_type === "CalendarEvent") {
        toast.success("Etkinlik oluşturuldu.", { duration: 2500 });
        onCreated?.(response.data);
        setDraft(EMPTY);
      } else if (!response.ok) {
        setError(response.error.user_message);
      } else {
        setError("Beklenmeyen bir cevap geldi.");
      }
    } catch (err) {
      setError(
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} data-testid="calendar-form" className="space-y-3">
      <Field
        label="Başlık"
        testId="field-title"
        value={draft.title}
        onChange={(v) => update("title", v)}
        placeholder="Etkinlik adı"
      />
      <Field
        label="Tarih"
        testId="field-date"
        type="date"
        value={draft.date}
        onChange={(v) => update("date", v)}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Başlangıç"
          testId="field-start"
          type="time"
          value={draft.startTime}
          onChange={(v) => update("startTime", v)}
        />
        <Field
          label="Bitiş"
          testId="field-end"
          type="time"
          value={draft.endTime}
          onChange={(v) => update("endTime", v)}
        />
      </div>
      {draft.startTime &&
        draft.endTime &&
        draft.startTime >= draft.endTime && (
          <p
            data-testid="form-time-warning"
            className="text-xs text-amber-300"
          >
            Bitiş zamanı başlangıçtan sonra olmalı.
          </p>
        )}
      <Field
        label="Detay"
        testId="field-detail"
        value={draft.detail}
        onChange={(v) => update("detail", v)}
        placeholder="Opsiyonel not"
        textarea
      />
      {error && (
        <div
          data-testid="form-error"
          className="rounded-md border border-rose-400/40 bg-rose-500/10 p-2 text-xs text-rose-100"
        >
          {error}
        </div>
      )}
      <button
        type="submit"
        data-testid="calendar-submit"
        disabled={!valid || submitting}
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition",
          "hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500",
        )}
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Oluşturuluyor…
          </>
        ) : (
          "Oluştur"
        )}
      </button>
    </form>
  );
}

interface FieldProps {
  label: string;
  testId: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  textarea?: boolean;
}

function Field({
  label,
  testId,
  value,
  onChange,
  placeholder,
  type = "text",
  textarea = false,
}: FieldProps) {
  const base =
    "w-full rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400";
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-400">
      {label}
      {textarea ? (
        <textarea
          data-testid={testId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className={`${base} resize-none`}
        />
      ) : (
        <input
          data-testid={testId}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={base}
        />
      )}
    </label>
  );
}
