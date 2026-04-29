import { ArrowLeft, FileText, Loader2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { askDocument, ChatNetworkError, sendChat } from "@/api/client";
import { BotAvatar } from "@/components/BotAvatar";
import { CapabilityModal } from "@/components/capability/CapabilityModal";
import { ChatInput } from "@/components/ChatInput";
import { MessageBubble } from "@/components/MessageBubble";
import { ShortcutBar, type CapabilityKey } from "@/components/ShortcutBar";
import { useConversation } from "@/store/conversation";
import { useDocumentContext } from "@/store/document";

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
  const activeDoc = useDocumentContext((s) => s.activeDoc);
  const clearActiveDoc = useDocumentContext((s) => s.clearActiveDoc);

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
      // When a document is active, every chat turn is a Q&A against
      // that doc — bypass the classifier so questions like "bu pdf ne
      // hakkında" route to DocumentStrategy with the doc_id the user
      // already uploaded. They dismiss via the banner to leave doc mode.
      if (activeDoc) {
        const response = await askDocument({
          doc_id: activeDoc.doc_id,
          question: text,
        });
        if (response.ok) {
          addMessage("assistant", response.data.answer);
        } else {
          addMessage("assistant", response.error.user_message);
          toast.error(response.error.user_message, { duration: 3000 });
        }
        return;
      }

      const result = await sendChat(text);
      if (result.ok) {
        const replyText = formatChatReply(result.ui_type, result.data, result.meta);
        const payload = isRichUiType(result.ui_type)
          ? {
              ui_type: result.ui_type,
              data: result.data,
              meta: result.meta ?? undefined,
            }
          : undefined;
        addMessage("assistant", replyText, payload);
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

      {activeDoc && (
        <div
          data-testid="active-doc-banner"
          className="flex items-center gap-2 border-t border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-100"
        >
          <FileText className="h-3.5 w-3.5 shrink-0" />
          <span className="min-w-0 flex-1 truncate">
            <span className="font-semibold">{activeDoc.original_name}</span>
            <span className="ml-2 text-emerald-200/70">
              · sorularını bu belgeye göre cevaplıyorum
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              clearActiveDoc();
              toast.info("Belge bağlamı kapatıldı — genel sohbete döndün.", {
                duration: 2000,
              });
            }}
            data-testid="clear-active-doc"
            aria-label="Belge bağlamını kapat"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-emerald-200 transition hover:bg-emerald-500/20"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

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

const RICH_UI_TYPES = new Set([
  "MailCard",
  "CalendarEvent",
  "EventList",
  "MailDraftCard",
]);

function isRichUiType(uiType: string): boolean {
  return RICH_UI_TYPES.has(uiType);
}

function formatChatReply(
  uiType: string,
  data: unknown,
  meta: Record<string, unknown> | null | undefined,
): string {
  // UI-specific renders take priority. meta.voice_summary is a one-line
  // headline meant for the voice surface; chat must show the full payload
  // (translation result, journal report markdown, etc.) when one exists.
  if (uiType === "TranslationCard" && isTranslationData(data)) {
    return `**${data.target_lang.toUpperCase()}**: ${data.translated_text}`;
  }
  if (uiType === "JournalReportCard" && isJournalReportData(data)) {
    return data.markdown;
  }
  // Fall back to voice_summary so capabilities without a chat-specific
  // formatter still produce a Turkish bubble instead of "İşlem tamamlandı."
  const voiceSummary = meta?.voice_summary;
  if (typeof voiceSummary === "string" && voiceSummary.trim()) {
    return voiceSummary;
  }
  if (typeof data === "string") return data;
  return "İşlem tamamlandı.";
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

function isJournalReportData(
  value: unknown,
): value is { markdown: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).markdown === "string"
  );
}
