import { useState, type FormEvent } from "react";

import { cn } from "@/lib/utils";

interface CalendarFormProps {
  onSubmit?: (draft: CalendarDraft) => void;
}

export interface CalendarDraft {
  title: string;
  date: string;
  time: string;
  detail: string;
}

const EMPTY: CalendarDraft = { title: "", date: "", time: "", detail: "" };

export function CalendarForm({ onSubmit }: CalendarFormProps) {
  const [draft, setDraft] = useState<CalendarDraft>(EMPTY);

  const update = (field: keyof CalendarDraft, value: string) =>
    setDraft((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit?.(draft);
  };

  const valid =
    draft.title.trim().length > 0 &&
    draft.date.trim().length > 0 &&
    draft.time.trim().length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="calendar-form"
      className="space-y-3"
    >
      <Field
        label="Başlık"
        testId="field-title"
        value={draft.title}
        onChange={(v) => update("title", v)}
        placeholder="Etkinlik adı"
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Tarih"
          testId="field-date"
          type="date"
          value={draft.date}
          onChange={(v) => update("date", v)}
        />
        <Field
          label="Saat"
          testId="field-time"
          type="time"
          value={draft.time}
          onChange={(v) => update("time", v)}
        />
      </div>
      <Field
        label="Detay"
        testId="field-detail"
        value={draft.detail}
        onChange={(v) => update("detail", v)}
        placeholder="Opsiyonel not"
        textarea
      />
      <button
        type="submit"
        data-testid="calendar-submit"
        disabled={!valid}
        className={cn(
          "w-full rounded-lg bg-sky-500 px-4 py-2 text-sm text-white transition",
          "hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500",
        )}
      >
        Oluştur (mock)
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
