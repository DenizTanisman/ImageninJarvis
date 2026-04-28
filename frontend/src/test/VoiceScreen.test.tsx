import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VoiceScreen } from "@/screens/VoiceScreen";
import { useConversation } from "@/store/conversation";

const sttState = {
  isSupported: true,
  isListening: false,
  transcript: "",
  interimTranscript: "",
  error: null as string | null,
  start: vi.fn(),
  stop: vi.fn(),
  reset: vi.fn(),
  onFinal: undefined as ((text: string) => void) | undefined,
  onError: undefined as ((code: string) => void) | undefined,
};

vi.mock("@/hooks/useSpeechRecognition", () => ({
  useSpeechRecognition: (opts?: {
    onFinal?: (t: string) => void;
    onError?: (c: string) => void;
  }) => {
    sttState.onFinal = opts?.onFinal;
    sttState.onError = opts?.onError;
    return {
      isSupported: sttState.isSupported,
      isListening: sttState.isListening,
      transcript: sttState.transcript,
      interimTranscript: sttState.interimTranscript,
      error: sttState.error,
      start: sttState.start,
      stop: sttState.stop,
      reset: sttState.reset,
    };
  },
}));

const ttsState = {
  isSupported: true,
  isSpeaking: false,
  speak: vi.fn(),
  cancel: vi.fn(),
};

vi.mock("@/hooks/useSpeechSynthesis", () => ({
  useSpeechSynthesis: () => ({
    isSupported: ttsState.isSupported,
    isSpeaking: ttsState.isSpeaking,
    speak: ttsState.speak,
    cancel: ttsState.cancel,
  }),
}));

const sendChatMock = vi.fn();
vi.mock("@/api/client", () => ({
  sendChat: (text: string) => sendChatMock(text),
  ChatNetworkError: class extends Error {},
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

beforeEach(() => {
  useConversation.getState().resetToGreeting();
  Object.assign(sttState, {
    isSupported: true,
    isListening: false,
    transcript: "",
    interimTranscript: "",
    error: null,
  });
  sttState.start.mockReset();
  sttState.stop.mockReset();
  sttState.reset.mockReset();
  ttsState.isSpeaking = false;
  ttsState.speak.mockReset();
  ttsState.cancel.mockReset();
  sendChatMock.mockReset();
});

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="current-path">{location.pathname}</div>;
}

function renderAt(path = "/voice") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<LocationProbe />} />
        <Route path="/voice" element={<VoiceScreen />} />
        <Route path="/chat" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VoiceScreen", () => {
  it("auto-starts speech recognition on mount when supported", () => {
    renderAt();
    expect(sttState.start).toHaveBeenCalledOnce();
  });

  it("does not auto-start when speech recognition is not supported", () => {
    sttState.isSupported = false;
    renderAt();
    expect(sttState.start).not.toHaveBeenCalled();
    expect(screen.getByTestId("voice-status")).toHaveTextContent(/desteklenmiyor/i);
  });

  it("renders pulsing avatar and bot status", () => {
    sttState.isListening = true;
    renderAt();
    expect(screen.getByRole("img", { name: /Jarvis bot avatar/i })).toBeInTheDocument();
    expect(screen.getByTestId("voice-status")).toHaveTextContent(/dinleniyor/i);
  });

  it("shows interim transcript while user is speaking", () => {
    sttState.isListening = true;
    sttState.interimTranscript = "merhaba dü";
    renderAt();
    expect(screen.getByTestId("voice-transcript")).toHaveTextContent("merhaba dü");
  });

  it("on final transcript: sends to backend, adds messages, speaks reply", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "text",
      data: "Selam dünya",
    });
    renderAt();
    expect(sttState.onFinal).toBeDefined();
    await act(async () => {
      sttState.onFinal!("merhaba");
    });

    await waitFor(() => expect(sendChatMock).toHaveBeenCalledWith("merhaba"));
    await waitFor(() => expect(ttsState.speak).toHaveBeenCalledWith("Selam dünya"));

    const messages = useConversation.getState().messages;
    const last = messages[messages.length - 1];
    expect(last.role).toBe("assistant");
    expect(last.text).toBe("Selam dünya");
  });

  it("on backend ok=false: shows user_message but does not crash", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "tekrar dener misin", retry_after: 10 },
    });
    renderAt();
    await act(async () => {
      sttState.onFinal!("hi");
    });
    await waitFor(() => {
      const msgs = useConversation.getState().messages;
      expect(msgs[msgs.length - 1].text).toMatch(/tekrar dener/i);
    });
  });

  it("renders friendly error when permission is denied", () => {
    sttState.error = "not-allowed";
    renderAt();
    expect(screen.getByTestId("voice-error")).toHaveTextContent(/reddedildi/i);
  });

  it("toggles mic stop when listening", async () => {
    sttState.isListening = true;
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("mic-toggle"));
    expect(sttState.stop).toHaveBeenCalled();
  });

  it("switch-to-chat navigates and stops speech + tts", async () => {
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("switch-to-chat"));
    expect(sttState.stop).toHaveBeenCalled();
    expect(ttsState.cancel).toHaveBeenCalled();
    expect(screen.getByTestId("current-path")).toHaveTextContent("/chat");
  });

  it("uses voice_summary from meta when present instead of structured data", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "MailCard",
      data: { categories: { important: [], dm: [], promo: [], other: [] } },
      meta: { voice_summary: "4 önemli, 2 promo mail var." },
    });
    renderAt();
    await act(async () => {
      sttState.onFinal!("bugün ne var");
    });
    await waitFor(() =>
      expect(ttsState.speak).toHaveBeenCalledWith("4 önemli, 2 promo mail var."),
    );
    const last = useConversation
      .getState()
      .messages.slice(-1)[0];
    expect(last.text).toBe("4 önemli, 2 promo mail var.");
  });

  it("falls back to data string when voice_summary is missing", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "text",
      data: "Selam!",
    });
    renderAt();
    await act(async () => {
      sttState.onFinal!("merhaba");
    });
    await waitFor(() => expect(ttsState.speak).toHaveBeenCalledWith("Selam!"));
  });

  it("barge-in: cancels TTS the moment user starts speaking", () => {
    ttsState.isSpeaking = true;
    sttState.interimTranscript = "ya";
    renderAt();
    expect(ttsState.cancel).toHaveBeenCalled();
  });

  it("no-speech error speaks the prompt back so the conversation loops", async () => {
    renderAt();
    expect(sttState.onError).toBeDefined();
    await act(async () => {
      sttState.onError!("no-speech");
    });
    expect(ttsState.speak).toHaveBeenCalledWith(
      expect.stringMatching(/duyamadım/i),
    );
  });
});
