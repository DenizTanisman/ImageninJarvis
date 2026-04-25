import {
  ArrowLeft,
  Mic,
  MicOff,
  MessageSquare,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { ChatNetworkError, sendChat } from "@/api/client";
import { BotAvatar } from "@/components/BotAvatar";
import { cn } from "@/lib/utils";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { useConversation } from "@/store/conversation";

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Mikrofon erişimi reddedildi. Tarayıcı ayarlarından izin ver.",
  "service-not-allowed": "Mikrofon erişimi reddedildi. Tarayıcı ayarlarından izin ver.",
  "audio-capture": "Mikrofon bulunamadı. Bağlı bir mikrofon olmalı.",
  network: "Konuşma servisine ulaşılamadı (network).",
  "no-speech": "Sesini duyamadım, tekrar dener misin?",
  unsupported: "Tarayıcın sesli moda destek vermiyor (Chrome veya Edge dene).",
  unknown: "Sesli mod hatası.",
};

export function VoiceScreen() {
  const navigate = useNavigate();
  const messageCount = useConversation((s) => s.messages.length);
  const addMessage = useConversation((s) => s.addMessage);

  const [isSending, setIsSending] = useState(false);
  const synth = useSpeechSynthesis();

  const handleFinal = useCallback(
    async (text: string) => {
      if (!text || isSending) return;
      addMessage("user", text);
      setIsSending(true);
      try {
        const result = await sendChat(text);
        const reply = result.ok
          ? typeof result.data === "string"
            ? result.data
            : JSON.stringify(result.data)
          : result.error.user_message;
        addMessage("assistant", reply);
        synth.speak(reply);
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
    },
    [addMessage, isSending, synth],
  );

  const handleError = useCallback((code: string) => {
    const msg = ERROR_MESSAGES[code] ?? ERROR_MESSAGES.unknown;
    if (code === "no-speech") {
      toast.info(msg, { duration: 2500 });
    } else {
      toast.error(msg, { duration: 3500 });
    }
  }, []);

  const recognition = useSpeechRecognition({
    onFinal: handleFinal,
    onError: handleError,
  });

  // Auto-start mic on mount when supported.
  useEffect(() => {
    if (!recognition.isSupported) return;
    recognition.start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recognition.isSupported]);

  const toggleMic = () => {
    if (recognition.isListening) {
      recognition.stop();
    } else {
      recognition.reset();
      recognition.start();
    }
  };

  const stopSpeaking = () => synth.cancel();

  const handleSwitchToChat = () => {
    recognition.stop();
    synth.cancel();
    navigate("/chat");
  };

  const visibleTranscript =
    recognition.transcript || recognition.interimTranscript;
  const status =
    !recognition.isSupported
      ? "Sesli mod desteklenmiyor"
      : isSending
        ? "Gönderiyor…"
        : synth.isSpeaking
          ? "Konuşuyor…"
          : recognition.isListening
            ? "Dinleniyor…"
            : "Mikrofon kapalı";

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-10 bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 px-6 text-slate-100">
      <button
        type="button"
        onClick={() => {
          recognition.stop();
          synth.cancel();
          navigate("/");
        }}
        data-testid="back-home"
        className="absolute left-4 top-4 flex items-center gap-1 rounded px-3 py-1 text-sm text-slate-300 transition hover:text-sky-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Ana ekran
      </button>

      <div className="flex flex-col items-center gap-4">
        <BotAvatar size="xl" pulse={recognition.isListening || synth.isSpeaking} />
        <p
          data-testid="voice-status"
          className="text-sm uppercase tracking-widest text-sky-300/70"
        >
          {status}
        </p>
        <p data-testid="voice-msg-count" className="text-xs text-slate-500">
          Geçmişte {messageCount} mesaj
        </p>
      </div>

      <div
        data-testid="voice-transcript"
        className={cn(
          "min-h-[3rem] max-w-md rounded-xl bg-slate-900/60 px-4 py-3 text-center text-sm text-slate-200 ring-1 ring-slate-700",
          visibleTranscript ? "" : "text-slate-500",
        )}
      >
        {visibleTranscript || "Konuşmaya başla, yazıya dökeyim."}
      </div>

      {recognition.error && (
        <p
          data-testid="voice-error"
          className="text-xs text-rose-300"
        >
          {ERROR_MESSAGES[recognition.error] ?? ERROR_MESSAGES.unknown}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleMic}
          disabled={!recognition.isSupported || isSending}
          data-testid="mic-toggle"
          aria-label={recognition.isListening ? "Mikrofonu kapat" : "Mikrofonu aç"}
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-full transition",
            recognition.isListening
              ? "bg-rose-500 text-white shadow-lg shadow-rose-500/40"
              : "bg-slate-800 text-sky-300 ring-1 ring-slate-700 hover:ring-sky-400",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {recognition.isListening ? (
            <MicOff className="h-5 w-5" />
          ) : (
            <Mic className="h-5 w-5" />
          )}
        </button>

        {synth.isSpeaking ? (
          <button
            type="button"
            onClick={stopSpeaking}
            data-testid="stop-speaking"
            aria-label="TTS'i durdur"
            className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-amber-300 ring-1 ring-slate-700 hover:ring-amber-400"
          >
            <VolumeX className="h-5 w-5" />
          </button>
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900/50 text-slate-600 ring-1 ring-slate-800">
            <Volume2 className="h-5 w-5" />
          </div>
        )}
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
