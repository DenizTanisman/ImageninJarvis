import { ArrowLeft, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { ChatNetworkError, sendChat } from "@/api/client";
import { BotAvatar } from "@/components/BotAvatar";
import { CapabilityModal } from "@/components/capability/CapabilityModal";
import { ChatInput } from "@/components/ChatInput";
import { MessageBubble } from "@/components/MessageBubble";
import { ShortcutBar, type CapabilityKey } from "@/components/ShortcutBar";
import { useConversation } from "@/store/conversation";

const STEP_TOAST: Partial<Record<CapabilityKey, string>> = {
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
  const [isSending, setIsSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length, isSending]);

  const handleSend = async (text: string) => {
    addMessage("user", text);
    setIsSending(true);
    try {
      const result = await sendChat(text);
      if (result.ok) {
        addMessage("assistant", formatChatReply(result.ui_type, result.data));
      } else {
        addMessage("assistant", result.error.user_message);
        toast.error(result.error.user_message, { duration: 3000 });
      }
    } catch (err) {
      const message =
        err instanceof ChatNetworkError
          ? err.message
          : "Beklenmeyen bir hata oluştu.";
      addMessage("assistant", message);
      toast.error(message, { duration: 3000 });
    } finally {
      setIsSending(false);
    }
  };

  const handleShortcut = (key: CapabilityKey) => {
    setActiveCapability(key);
    const toastText = STEP_TOAST[key];
    if (toastText) {
      toast.info(toastText, { duration: 2500 });
    }
  };

  const handleVoicePress = () => {
    toast.info("Sesli mod Step 1.7'de devreye girecek.", { duration: 2000 });
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
        {isSending && (
          <div
            data-testid="typing-indicator"
            className="flex items-center gap-2 px-4 text-xs text-slate-400"
          >
            <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
            Düşünüyor…
          </div>
        )}
      </section>

      <ChatInput
        onSend={handleSend}
        onVoicePress={handleVoicePress}
        disabled={isSending}
      />

      <CapabilityModal
        capability={activeCapability}
        onOpenChange={(open) => !open && setActiveCapability(null)}
      />
    </div>
  );
}

function formatChatReply(uiType: string, data: unknown): string {
  if (uiType === "TranslationCard" && isTranslationData(data)) {
    return `**${data.target_lang.toUpperCase()}**: ${data.translated_text}`;
  }
  if (typeof data === "string") return data;
  return JSON.stringify(data);
}

function isTranslationData(
  value: unknown,
): value is { translated_text: string; target_lang: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).translated_text === "string" &&
    typeof (value as Record<string, unknown>).target_lang === "string"
  );
}
