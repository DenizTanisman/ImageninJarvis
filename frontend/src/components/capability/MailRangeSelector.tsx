import { useMailUI, type MailRangeKind } from "@/store/mail";
import { cn } from "@/lib/utils";

const OPTIONS: Array<{ key: MailRangeKind; label: string }> = [
  { key: "daily", label: "Günlük" },
  { key: "weekly", label: "Haftalık" },
  { key: "custom", label: "Özel aralık" },
];

export function MailRangeSelector() {
  const range = useMailUI((s) => s.range);
  const setRangeKind = useMailUI((s) => s.setRangeKind);
  const setCustomAfter = useMailUI((s) => s.setCustomAfter);
  const setCustomBefore = useMailUI((s) => s.setCustomBefore);

  return (
    <div data-testid="mail-range-selector" className="space-y-3">
      <div className="flex gap-2">
        {OPTIONS.map((opt) => {
          const active = range.kind === opt.key;
          return (
            <button
              key={opt.key}
              type="button"
              data-testid={`range-${opt.key}`}
              onClick={() => setRangeKind(opt.key)}
              className={cn(
                "flex-1 rounded-lg border px-3 py-2 text-xs transition",
                active
                  ? "border-sky-400 bg-sky-500/10 text-sky-200 ring-2 ring-sky-400/40"
                  : "border-slate-700 bg-slate-900/60 text-slate-300 hover:border-sky-400/60",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {range.kind === "custom" && (
        <div
          data-testid="custom-range-fields"
          className="grid grid-cols-2 gap-2 rounded-lg border border-slate-700 bg-slate-900/40 p-3"
        >
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Başlangıç
            <input
              type="date"
              data-testid="range-custom-after"
              value={range.customAfter}
              max={range.customBefore}
              onChange={(e) => setCustomAfter(e.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Bitiş
            <input
              type="date"
              data-testid="range-custom-before"
              value={range.customBefore}
              min={range.customAfter}
              onChange={(e) => setCustomBefore(e.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 focus:border-sky-400 focus:outline-none"
            />
          </label>
        </div>
      )}
    </div>
  );
}
