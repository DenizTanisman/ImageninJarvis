import { ArrowLeft, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { BotAvatar } from "@/components/BotAvatar";
import { useConversation } from "@/store/conversation";

export function VoiceScreen() {
  const navigate = useNavigate();
  const messageCount = useConversation((s) => s.messages.length);

  const handleSwitchToChat = () => {
    toast.info("Genel LLM henüz bağlı değil — Step 1'de gelecek.", {
      duration: 2500,
    });
    navigate("/chat");
  };

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-12 bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 text-slate-100">
      <button
        type="button"
        onClick={() => navigate("/")}
        data-testid="back-home"
        className="absolute left-4 top-4 flex items-center gap-1 rounded px-3 py-1 text-sm text-slate-300 transition hover:text-sky-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Ana ekran
      </button>

      <div className="flex flex-col items-center gap-4">
        <BotAvatar size="xl" pulse />
        <p className="text-sm uppercase tracking-widest text-sky-300/70">
          Dinleniyor…
        </p>
        <p
          data-testid="voice-msg-count"
          className="text-xs text-slate-500"
        >
          Geçmişte {messageCount} mesaj
        </p>
      </div>

      <button
        type="button"
        onClick={handleSwitchToChat}
        data-testid="switch-to-chat"
        className="flex items-center gap-2 rounded-full bg-slate-800/80 px-6 py-3 text-sm text-slate-100 ring-1 ring-sky-400/30 transition hover:bg-slate-800 hover:ring-sky-400/70"
      >
        <MessageSquare className="h-4 w-4" />
        Chat'e geç
      </button>
    </main>
  );
}
