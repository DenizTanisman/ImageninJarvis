import { ArrowDownUp, Copy, Languages, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ChatNetworkError, translate } from "@/api/client";
import { TRANSLATION_LANGS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const TARGET_LANGS = TRANSLATION_LANGS;
const SOURCE_LANGS = [{ code: "auto", label: "Otomatik" }, ...TRANSLATION_LANGS];

interface LangPickerProps {
  value: string;
  onChange: (code: string) => void;
  testId: string;
  options: { code: string; label: string }[];
  disabled?: boolean;
}

function LangPicker({ value, onChange, testId, options, disabled }: LangPickerProps) {
  return (
    <select
      data-testid={testId}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-400 disabled:opacity-50"
    >
      {options.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.label}
        </option>
      ))}
    </select>
  );
}

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string };

export function TranslationCard() {
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("en");
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const swap = () => {
    // Auto can't be a target — pick a sensible fallback.
    const newSource = targetLang;
    const newTarget = sourceLang === "auto" ? "tr" : sourceLang;
    setSourceLang(newSource);
    setTargetLang(newTarget);
    setSource(target);
    setTarget(source);
  };

  const copy = (text: string, label: string) => {
    if (!text) return;
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
      toast.success(`${label} kopyalandı.`, { duration: 1500 });
    }
  };

  const runTranslate = async () => {
    const trimmed = source.trim();
    if (!trimmed) {
      setStatus({ kind: "error", message: "Çevirmek istediğin metni yaz." });
      return;
    }
    setStatus({ kind: "loading" });
    setTarget("");
    try {
      const result = await translate({
        text: trimmed,
        source: sourceLang,
        target: targetLang,
      });
      if (result.ok) {
        setTarget(result.data.translated_text);
        setStatus({ kind: "idle" });
      } else {
        setStatus({ kind: "error", message: result.error.user_message });
      }
    } catch (err) {
      const message =
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.";
      setStatus({ kind: "error", message });
    }
  };

  const isLoading = status.kind === "loading";

  return (
    <div data-testid="translation-card" className="space-y-3">
      <Pane
        label="Kaynak"
        lang={sourceLang}
        langOptions={SOURCE_LANGS}
        onLangChange={setSourceLang}
        langTestId="lang-source"
        value={source}
        onChange={setSource}
        onCopy={() => copy(source, "Kaynak")}
        readOnly={false}
        testId="source-pane"
        disabled={isLoading}
      />

      <div className="flex justify-center">
        <button
          type="button"
          onClick={swap}
          disabled={isLoading}
          data-testid="swap-button"
          aria-label="Dilleri değiştir"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-sky-300 ring-1 ring-slate-700 transition hover:ring-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ArrowDownUp className="h-4 w-4" />
        </button>
      </div>

      <Pane
        label="Hedef"
        lang={targetLang}
        langOptions={TARGET_LANGS}
        onLangChange={setTargetLang}
        langTestId="lang-target"
        value={target}
        onChange={setTarget}
        onCopy={() => copy(target, "Çeviri")}
        readOnly
        testId="target-pane"
        disabled={isLoading}
      />

      {status.kind === "error" && (
        <div
          data-testid="translation-error"
          className="rounded-md border border-rose-400/40 bg-rose-500/10 p-2 text-xs text-rose-100"
        >
          {status.message}
        </div>
      )}

      <button
        type="button"
        onClick={runTranslate}
        disabled={isLoading || source.trim().length === 0}
        data-testid="translate-button"
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Çeviriliyor…
          </>
        ) : (
          <>
            <Languages className="h-4 w-4" />
            Çevir
          </>
        )}
      </button>
    </div>
  );
}

interface PaneProps {
  label: string;
  lang: string;
  langOptions: { code: string; label: string }[];
  onLangChange: (code: string) => void;
  langTestId: string;
  value: string;
  onChange: (text: string) => void;
  onCopy: () => void;
  readOnly: boolean;
  testId: string;
  disabled?: boolean;
}

function Pane({
  label,
  lang,
  langOptions,
  onLangChange,
  langTestId,
  value,
  onChange,
  onCopy,
  readOnly,
  testId,
  disabled,
}: PaneProps) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <LangPicker
            value={lang}
            onChange={onLangChange}
            testId={langTestId}
            options={langOptions}
            disabled={disabled}
          />
          <button
            type="button"
            onClick={onCopy}
            aria-label={`${label} metni kopyala`}
            className="text-slate-400 transition hover:text-sky-300"
          >
            <Copy className="h-4 w-4" />
          </button>
        </div>
      </div>
      <textarea
        data-testid={testId}
        value={value}
        readOnly={readOnly}
        disabled={disabled && !readOnly}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        placeholder={
          readOnly ? "Çeviri burada görünecek…" : "Çevirmek istediğin metni yaz…"
        }
        className={cn(
          "w-full resize-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-600",
          readOnly && "text-slate-200",
        )}
      />
    </div>
  );
}
