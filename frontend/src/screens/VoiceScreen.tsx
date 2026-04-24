import { useNavigate } from "react-router-dom";

import { BotAvatar } from "@/components/BotAvatar";

export function VoiceScreen() {
  const navigate = useNavigate();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 text-slate-100">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="absolute left-4 top-4 rounded px-3 py-1 text-sm text-slate-300 hover:text-sky-300"
        data-testid="back-home"
      >
        &lt; Ana ekran
      </button>
      <BotAvatar size="xl" />
      <p className="text-lg text-slate-200">Sesli mod — Step 0.3'te dolacak</p>
    </main>
  );
}
