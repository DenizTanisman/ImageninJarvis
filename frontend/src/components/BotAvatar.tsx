import { cn } from "@/lib/utils";

type Size = "sm" | "md" | "lg" | "xl";

const sizeClass: Record<Size, string> = {
  sm: "h-10 w-10",
  md: "h-16 w-16",
  lg: "h-32 w-32",
  xl: "h-48 w-48",
};

interface BotAvatarProps {
  size?: Size;
  pulse?: boolean;
  className?: string;
}

export function BotAvatar({ size = "lg", pulse = false, className }: BotAvatarProps) {
  return (
    <div
      aria-label="Jarvis bot avatar"
      role="img"
      className={cn(
        "relative flex items-center justify-center rounded-full bg-slate-900 shadow-xl ring-4 ring-sky-400/30",
        sizeClass[size],
        pulse && "animate-pulse",
        className,
      )}
    >
      <img src="/jarvis.svg" alt="" className="h-3/4 w-3/4" />
    </div>
  );
}
