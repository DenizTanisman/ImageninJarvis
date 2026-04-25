import { CalendarDays, FileText, Languages, Mail } from "lucide-react";
import { type ComponentType, type SVGProps } from "react";

import { cn } from "@/lib/utils";

export type CapabilityKey = "mail" | "translation" | "calendar" | "document";

interface ShortcutDef {
  key: CapabilityKey;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  accent: string;
}

const SHORTCUTS: ShortcutDef[] = [
  { key: "mail", label: "Mail", icon: Mail, accent: "text-rose-300" },
  { key: "translation", label: "Çeviri", icon: Languages, accent: "text-emerald-300" },
  { key: "calendar", label: "Takvim", icon: CalendarDays, accent: "text-amber-300" },
  { key: "document", label: "Döküman", icon: FileText, accent: "text-sky-300" },
];

interface ShortcutBarProps {
  onSelect: (key: CapabilityKey) => void;
  activeKey?: CapabilityKey | null;
}

export function ShortcutBar({ onSelect, activeKey }: ShortcutBarProps) {
  return (
    <nav
      aria-label="Capability shortcuts"
      className="flex w-full items-center justify-center gap-2 border-b border-slate-800 bg-slate-950/60 px-4 py-3 backdrop-blur"
    >
      {SHORTCUTS.map(({ key, label, icon: Icon, accent }) => {
        const isActive = activeKey === key;
        return (
          <button
            key={key}
            type="button"
            data-testid={`shortcut-${key}`}
            onClick={() => onSelect(key)}
            className={cn(
              "flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition",
              "border-slate-700 bg-slate-900/70 text-slate-200",
              "hover:border-sky-400/60 hover:text-sky-200",
              isActive && "border-sky-400 text-sky-200 ring-2 ring-sky-400/40",
            )}
          >
            <Icon className={cn("h-4 w-4", accent)} />
            {label}
          </button>
        );
      })}
    </nav>
  );
}
