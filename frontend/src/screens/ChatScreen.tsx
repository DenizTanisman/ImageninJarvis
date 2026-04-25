import { ArrowLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { BotAvatar } from "@/components/BotAvatar";
import { CapabilityModal } from "@/components/capability/CapabilityModal";
import { ChatInput } from "@/components/ChatInput";
import { MessageBubble } from "@/components/MessageBubble";
import { ShortcutBar, type CapabilityKey } from "@/components/ShortcutBar";
import { useConversation } from "@/store/conversation";

const STEP_TOAST: Record<CapabilityKey, string> = {
  mail: "Mail özeti Step 2'de gelecek.",
  translation: "Çeviri Step 3'te gelecek.",
  calendar: "Takvim Step 4'te gelecek.",
  document: "Döküman Q&A Step 5'te gelecek.",
};

export function ChatScreen() {
  const navigate = useNavigate();
  const messages = useConversation((s) => s.messages);
  const addMessage = useConversation((s) => s.addMessage);

  const [activeCapability, setActiveCapability] = useState<CapabilityKey | null>(
    null,
  );
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length]);

  const handleSend = (text: string) => {
    addMessage("user", text);
    toast.info("LLM henüz bağlı değil — Step 1'de gelecek.", { duration: 2500 });
  };

  const handleShortcut = (key: CapabilityKey) => {
    setActiveCapability(key);
    toast.info(STEP_TOAST[key], { duration: 2500 });
  };

  const handleVoicePress = () => {
    toast.info("Sesli mod Step 1'de devreye girecek.", { duration: 2000 });
    navigate("/voice");
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 text-slate-100">
      <header className="flex items-center gap-3 border-b border-slate-800 bg-slate-950/70 px-4 py-3 backdrop-blur">
        <button
          type="button"
          onClick={() => navigate("/")}
          data-testid="back-home"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-400 transition hover:text-sky-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Ana
        </button>
        <BotAvatar size="sm" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-slate-100">Jarvis</span>
          <span className="text-xs text-slate-500">Sohbet modu</span>
        </div>
      </header>

      <ShortcutBar onSelect={handleShortcut} activeKey={activeCapability} />

      <section
        ref={listRef}
        aria-label="Mesaj listesi"
        data-testid="message-list"
        className="flex-1 space-y-3 overflow-y-auto px-4 py-6"
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </section>

      <ChatInput onSend={handleSend} onVoicePress={handleVoicePress} />

      <CapabilityModal
        capability={activeCapability}
        onOpenChange={(open) => !open && setActiveCapability(null)}
      />
    </div>
  );
}
