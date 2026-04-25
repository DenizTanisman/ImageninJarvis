import { useCallback, useEffect, useRef, useState } from "react";

type RecognitionConstructor = new () => SpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

export type SpeechRecognitionErrorCode =
  | "no-speech"
  | "audio-capture"
  | "not-allowed"
  | "service-not-allowed"
  | "aborted"
  | "network"
  | "language-not-supported"
  | "bad-grammar"
  | "unsupported"
  | "unknown";

interface UseSpeechRecognitionOptions {
  lang?: string;
  interimResults?: boolean;
  onFinal?: (transcript: string) => void;
  onError?: (code: SpeechRecognitionErrorCode) => void;
}

interface UseSpeechRecognitionReturn {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: SpeechRecognitionErrorCode | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

function getRecognitionCtor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function useSpeechRecognition({
  lang = "tr-TR",
  interimResults = true,
  onFinal,
  onError,
}: UseSpeechRecognitionOptions = {}): UseSpeechRecognitionReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<SpeechRecognitionErrorCode | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalRef = useRef("");

  const Ctor = getRecognitionCtor();
  const isSupported = Ctor !== null;

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    finalRef.current = "";
    setTranscript("");
    setInterimTranscript("");
    setError(null);
  }, []);

  const start = useCallback(() => {
    if (!Ctor) {
      setError("unsupported");
      onError?.("unsupported");
      return;
    }
    if (recognitionRef.current) return;

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.interimResults = interimResults;
    recognition.continuous = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let appended = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0]?.transcript ?? "";
        if (result.isFinal) {
          appended += text;
        } else {
          interim += text;
        }
      }
      if (appended) {
        finalRef.current = `${finalRef.current}${appended}`.trim();
        setTranscript(finalRef.current);
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = (event.error as SpeechRecognitionErrorCode) ?? "unknown";
      setError(code);
      onError?.(code);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript("");
      recognitionRef.current = null;
      const finalText = finalRef.current.trim();
      if (finalText) {
        onFinal?.(finalText);
      }
    };

    finalRef.current = "";
    setTranscript("");
    setInterimTranscript("");
    setError(null);
    setIsListening(true);
    recognitionRef.current = recognition;
    recognition.start();
  }, [Ctor, interimResults, lang, onError, onFinal]);

  useEffect(
    () => () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    },
    [],
  );

  return {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    error,
    start,
    stop,
    reset,
  };
}
