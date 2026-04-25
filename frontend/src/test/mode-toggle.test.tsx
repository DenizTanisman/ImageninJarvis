import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import { useConversation } from "@/store/conversation";
import { useMode } from "@/store/mode";

let capturedOnFinal: ((text: string) => void) | undefined;

vi.mock("@/hooks/useSpeechRecognition", () => ({
  useSpeechRecognition: ({ onFinal }: { onFinal?: (t: string) => void }) => {
    capturedOnFinal = onFinal;
    return {
      isSupported: true,
      isListening: true,
      transcript: "",
      interimTranscript: "",
      error: null,
      start: vi.fn(),
      stop: vi.fn(),
      reset: vi.fn(),
    };
  },
}));

vi.mock("@/hooks/useSpeechSynthesis", () => ({
  useSpeechSynthesis: () => ({
    isSupported: true,
    isSpeaking: false,
    speak: vi.fn(),
    cancel: vi.fn(),
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
  useMode.setState({ mode: "home" });
  window.history.pushState({}, "", "/");
  capturedOnFinal = undefined;
  sendChatMock.mockReset();
});

describe("mode toggle continuity (voice → chat)", () => {
  it("messages spoken in voice mode are visible in chat mode", async () => {
    sendChatMock
      .mockResolvedValueOnce({ ok: true, ui_type: "text", data: "Cevap 1" })
      .mockResolvedValueOnce({ ok: true, ui_type: "text", data: "Cevap 2" });

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByTestId("nav-voice"));
    expect(useMode.getState().mode).toBe("voice");
    expect(capturedOnFinal).toBeDefined();

    await act(async () => {
      capturedOnFinal!("ses ile birinci");
    });
    await waitFor(() =>
      expect(sendChatMock).toHaveBeenCalledWith("ses ile birinci"),
    );
    await waitFor(() =>
      expect(useConversation.getState().messages).toHaveLength(3),
    );

    await act(async () => {
      capturedOnFinal!("ses ile ikinci");
    });
    await waitFor(() =>
      expect(sendChatMock).toHaveBeenCalledWith("ses ile ikinci"),
    );
    await waitFor(() =>
      expect(useConversation.getState().messages).toHaveLength(5),
    );

    await user.click(screen.getByTestId("switch-to-chat"));
    expect(useMode.getState().mode).toBe("chat");

    const list = screen.getByTestId("message-list");
    expect(within(list).getByText("ses ile birinci")).toBeInTheDocument();
    expect(within(list).getByText("Cevap 1")).toBeInTheDocument();
    expect(within(list).getByText("ses ile ikinci")).toBeInTheDocument();
    expect(within(list).getByText("Cevap 2")).toBeInTheDocument();
    expect(
      within(list).getByText(/nasıl yardımcı olabilirim/i),
    ).toBeInTheDocument();
  });

  it("chat → home → voice round trip preserves history and updates mode", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "text",
      data: "yazılı cevap",
    });
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByTestId("nav-chat"));
    expect(useMode.getState().mode).toBe("chat");

    const input = screen.getByTestId("chat-input");
    await user.type(input, "yazılı mesaj");
    await user.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(useConversation.getState().messages).toHaveLength(3),
    );

    await user.click(screen.getByTestId("back-home"));
    expect(useMode.getState().mode).toBe("home");

    await user.click(screen.getByTestId("nav-voice"));
    expect(useMode.getState().mode).toBe("voice");
    expect(screen.getByTestId("voice-msg-count")).toHaveTextContent(/3 mesaj/);

    await user.click(screen.getByTestId("switch-to-chat"));
    expect(useMode.getState().mode).toBe("chat");
    expect(
      within(screen.getByTestId("message-list")).getByText("yazılı mesaj"),
    ).toBeInTheDocument();
  });
});
