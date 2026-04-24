import { Mic, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { BotAvatar } from "@/components/BotAvatar";
import { cn } from "@/lib/utils";

interface NavButtonProps {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  testId: string;
}

function NavButton({ label, icon, onClick, testId }: NavButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      aria-label={label}
      className={cn(
        "flex h-20 w-20 items-center justify-center rounded-full",
        "bg-slate-900 text-sky-300 shadow-lg ring-2 ring-sky-400/30",
        "transition hover:scale-105 hover:shadow-sky-400/40 hover:ring-sky-400/70",
        "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-400",
      )}
    >
      {icon}
    </button>
  );
}

export function HomeScreen() {
  const navigate = useNavigate();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 text-foreground">
      <h1 className="text-3xl font-semibold tracking-tight text-sky-100">Jarvis</h1>

      <div className="flex items-center justify-center gap-10">
        <NavButton
          label="Sesli moda geç"
          icon={<Mic className="h-8 w-8" />}
          onClick={() => navigate("/voice")}
          testId="nav-voice"
        />

        <BotAvatar size="xl" />

        <NavButton
          label="Sohbete geç"
          icon={<MessageSquare className="h-8 w-8" />}
          onClick={() => navigate("/chat")}
          testId="nav-chat"
        />
      </div>

      <p className="text-sm text-slate-400">
        Sol: sesli mod · Sağ: sohbet modu
      </p>
    </main>
  );
}
