import {
  AlertTriangle,
  ListChecks,
  ScrollText,
  Sparkles,
} from "lucide-react";
import { type ComponentType, type SVGProps } from "react";

import { cn } from "@/lib/utils";

interface JournalTag {
  tag: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  accent: string;
  hint: string;
}

// Five capabilities the Journal AI Reporter exposes; /date{...} stays a typed
// command since it needs a calendar date and a chip would be misleading.
const JOURNAL_TAGS: JournalTag[] = [
  {
    tag: "/detail",
    label: "Detay",
    icon: ScrollText,
    accent: "text-sky-300",
    hint: "Tüm kategoriler — özet, yapılacaklar, kaygılar, başarılar, öneri",
  },
  {
    tag: "/todo",
    label: "Yapılacaklar",
    icon: ListChecks,
    accent: "text-amber-300",
    hint: "Açık / tamamlanan / ertelenmiş + analiz",
  },
  {
    tag: "/concern",
    label: "Kaygılar",
    icon: AlertTriangle,
    accent: "text-rose-300",
    hint: "Anksiyete / korku / başarısızlık + empatik özet",
  },
  {
    tag: "/success",
    label: "Başarılar",
    icon: Sparkles,
    accent: "text-emerald-300",
    hint: "Kazanımlar / kilometre taşları / pozitif anlar",
  },
];

interface JournalQuickbarProps {
  onSelect: (tag: string) => void;
  disabled?: boolean;
}

export function JournalQuickbar({ onSelect, disabled }: JournalQuickbarProps) {
  return (
    <nav
      aria-label="Günlük rapor kısayolları"
      data-testid="journal-quickbar"
      className="flex items-center gap-2 overflow-x-auto border-t border-slate-800 bg-slate-950/40 px-4 py-2 backdrop-blur"
    >
      <span className="shrink-0 text-[11px] uppercase tracking-wider text-slate-500">
        Günlük
      </span>
      {JOURNAL_TAGS.map(({ tag, label, icon: Icon, accent, hint }) => (
        <button
          key={tag}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(tag)}
          title={hint}
          data-testid={`journal-tag-${tag.slice(1)}`}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition",
            "border-slate-700 bg-slate-900/70 text-slate-200",
            "hover:border-sky-400/60 hover:text-sky-200",
            disabled && "cursor-not-allowed opacity-50 hover:border-slate-700 hover:text-slate-200",
          )}
        >
          <Icon className={cn("h-3.5 w-3.5", accent)} />
          {label}
          <span className="font-mono text-[10px] text-slate-500">{tag}</span>
        </button>
      ))}
    </nav>
  );
}
