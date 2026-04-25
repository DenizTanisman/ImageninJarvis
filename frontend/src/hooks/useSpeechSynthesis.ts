import { useCallback, useEffect, useState } from "react";

interface UseSpeechSynthesisReturn {
  isSupported: boolean;
  isSpeaking: boolean;
  speak: (text: string, lang?: string) => void;
  cancel: () => void;
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
  const isSupported =
    typeof window !== "undefined" &&
    typeof window.speechSynthesis !== "undefined";

  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = useCallback(
    (text: string, lang = "tr-TR") => {
      if (!isSupported || !text.trim()) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [isSupported],
  );

  const cancel = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, [isSupported]);

  useEffect(
    () => () => {
      if (isSupported) {
        window.speechSynthesis.cancel();
      }
    },
    [isSupported],
  );

  return { isSupported, isSpeaking, speak, cancel };
}
