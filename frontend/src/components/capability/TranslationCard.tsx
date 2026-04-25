import { ArrowDownUp, Copy } from "lucide-react";
import { useState } from "react";

import { MOCK_TRANSLATION, TRANSLATION_LANGS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

interface LangPickerProps {
  value: string;
  onChange: (code: string) => void;
  testId: string;
}

function LangPicker({ value, onChange, testId }: LangPickerProps) {
  return (
    <select
      data-testid={testId}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-400"
    >
      {TRANSLATION_LANGS.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.label}
        </option>
      ))}
    </select>
  );
}

export function TranslationCard() {
  const [sourceLang, setSourceLang] = useState(MOCK_TRANSLATION.sourceLang);
  const [targetLang, setTargetLang] = useState(MOCK_TRANSLATION.targetLang);
  const [source, setSource] = useState(MOCK_TRANSLATION.source);
  const [target, setTarget] = useState(MOCK_TRANSLATION.target);

  const swap = () => {
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
    setSource(target);
    setTarget(source);
  };

  const copy = (text: string) => {
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
  };

  return (
    <div data-testid="translation-card" className="space-y-3">
      <Pane
        label="Kaynak"
        lang={sourceLang}
        onLangChange={setSourceLang}
        langTestId="lang-source"
        value={source}
        onChange={setSource}
        onCopy={() => copy(source)}
        readOnly={false}
        testId="source-pane"
      />

      <div className="flex justify-center">
        <button
          type="button"
          onClick={swap}
          data-testid="swap-button"
          aria-label="Dilleri değiştir"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-sky-300 ring-1 ring-slate-700 transition hover:ring-sky-400"
        >
          <ArrowDownUp className="h-4 w-4" />
        </button>
      </div>

      <Pane
        label="Hedef"
        lang={targetLang}
        onLangChange={setTargetLang}
        langTestId="lang-target"
        value={target}
        onChange={setTarget}
        onCopy={() => copy(target)}
        readOnly
        testId="target-pane"
      />
    </div>
  );
}

interface PaneProps {
  label: string;
  lang: string;
  onLangChange: (code: string) => void;
  langTestId: string;
  value: string;
  onChange: (text: string) => void;
  onCopy: () => void;
  readOnly: boolean;
  testId: string;
}

function Pane({
  label,
  lang,
  onLangChange,
  langTestId,
  value,
  onChange,
  onCopy,
  readOnly,
  testId,
}: PaneProps) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <LangPicker value={lang} onChange={onLangChange} testId={langTestId} />
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
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className={cn(
          "w-full resize-none bg-transparent text-sm text-slate-100 outline-none",
          readOnly && "text-slate-200",
        )}
      />
    </div>
  );
}
