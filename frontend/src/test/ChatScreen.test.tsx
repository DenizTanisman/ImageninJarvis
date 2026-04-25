import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatScreen } from "@/screens/ChatScreen";
import { useConversation } from "@/store/conversation";

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
  sendChatMock.mockReset();
});

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="current-path">{location.pathname}</div>;
}

function renderAt(path = "/chat") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<LocationProbe />} />
        <Route path="/voice" element={<LocationProbe />} />
        <Route path="/chat" element={<ChatScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ChatScreen", () => {
  it("renders header, shortcut bar, welcome message and input", () => {
    renderAt();
    expect(screen.getByRole("img", { name: /Jarvis bot avatar/i })).toBeInTheDocument();
    expect(screen.getByTestId("shortcut-mail")).toBeInTheDocument();
    expect(screen.getByText(/nasıl yardımcı olabilirim/i)).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("appends user message + assistant reply on successful send", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "text",
      data: "Merhaba!",
    });
    const user = userEvent.setup();
    renderAt();

    await user.type(screen.getByTestId("chat-input"), "Selam");
    await user.click(screen.getByTestId("send-button"));

    const list = screen.getByTestId("message-list");
    expect(within(list).getByText("Selam")).toBeInTheDocument();
    await waitFor(() =>
      expect(within(list).getByText("Merhaba!")).toBeInTheDocument(),
    );
    expect(sendChatMock).toHaveBeenCalledWith("Selam");
  });

  it("renders typing indicator while waiting for response", async () => {
    let resolveCall: (value: { ok: true; ui_type: string; data: string }) => void;
    const pending = new Promise<{ ok: true; ui_type: string; data: string }>(
      (resolve) => {
        resolveCall = resolve;
      },
    );
    sendChatMock.mockReturnValueOnce(pending);
    const user = userEvent.setup();
    renderAt();

    await user.type(screen.getByTestId("chat-input"), "test");
    await user.click(screen.getByTestId("send-button"));

    expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeDisabled();

    resolveCall!({ ok: true, ui_type: "text", data: "ok" });
    await waitFor(() =>
      expect(screen.queryByTestId("typing-indicator")).toBeNull(),
    );
  });

  it("shows backend error message when ok=false", async () => {
    sendChatMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Tekrar dener misin?", retry_after: 10 },
    });
    const user = userEvent.setup();
    renderAt();
    await user.type(screen.getByTestId("chat-input"), "ping");
    await user.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(
        within(screen.getByTestId("message-list")).getByText(
          /tekrar dener misin/i,
        ),
      ).toBeInTheDocument(),
    );
  });

  it("shows network error when sendChat throws", async () => {
    sendChatMock.mockRejectedValueOnce(new Error("Backend down"));
    const user = userEvent.setup();
    renderAt();
    await user.type(screen.getByTestId("chat-input"), "ping");
    await user.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(
        within(screen.getByTestId("message-list")).getByText(
          /beklenmeyen|hata/i,
        ),
      ).toBeInTheDocument(),
    );
  });

  it("opens mail modal when mail shortcut clicked", async () => {
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("shortcut-mail"));
    expect(await screen.findByTestId("modal-mail")).toBeInTheDocument();
  });

  it("voice toggle navigates to /voice", async () => {
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("voice-toggle"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/voice");
  });

  it("back button returns to home", async () => {
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("back-home"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/");
  });
});
