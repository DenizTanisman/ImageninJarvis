import { Mic, Send } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (text: string) => void;
  onVoicePress: () => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, onVoicePress, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 border-t border-slate-800 bg-slate-950/80 p-3 backdrop-blur"
    >
      <textarea
        data-testid="chat-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Mesajını yaz veya sol alttaki mikrofona bas…"
        rows={1}
        disabled={disabled}
        className={cn(
          "min-h-[44px] max-h-40 flex-1 resize-none rounded-xl bg-slate-900/80 px-4 py-2.5",
          "text-sm text-slate-100 placeholder:text-slate-500",
          "outline-none ring-1 ring-slate-700 focus:ring-2 focus:ring-sky-400",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
      />
      <button
        type="button"
        data-testid="voice-toggle"
        onClick={onVoicePress}
        aria-label="Sesli konuş"
        className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-900 text-sky-300 ring-1 ring-slate-700 transition hover:ring-sky-400"
      >
        <Mic className="h-5 w-5" />
      </button>
      <button
        type="submit"
        data-testid="send-button"
        disabled={disabled || value.trim().length === 0}
        aria-label="Gönder"
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-full transition",
          "bg-sky-500 text-white hover:bg-sky-400",
          "disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500",
        )}
      >
        <Send className="h-5 w-5" />
      </button>
    </form>
  );
}
