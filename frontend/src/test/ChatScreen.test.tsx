import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatScreen } from "@/screens/ChatScreen";
import { useConversation } from "@/store/conversation";

vi.mock("sonner", () => ({
  toast: { info: vi.fn() },
  Toaster: () => null,
}));

beforeEach(() => {
  useConversation.getState().resetToGreeting();
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
    expect(screen.getByTestId("shortcut-translation")).toBeInTheDocument();
    expect(screen.getByTestId("shortcut-calendar")).toBeInTheDocument();
    expect(screen.getByTestId("shortcut-document")).toBeInTheDocument();
    expect(screen.getByText(/nasıl yardımcı olabilirim/i)).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("appends user message and fires Step-1 toast on send", async () => {
    const { toast } = await import("sonner");
    const user = userEvent.setup();
    renderAt();
    const input = screen.getByTestId("chat-input");
    await user.type(input, "Merhaba");
    const send = screen.getByTestId("send-button");
    expect(send).toBeEnabled();
    await user.click(send);
    const list = screen.getByTestId("message-list");
    expect(within(list).getByText("Merhaba")).toBeInTheDocument();
    expect(toast.info).toHaveBeenCalledWith(
      expect.stringContaining("Step 1"),
      expect.anything(),
    );
  });

  it("opens mail modal and fires toast when mail shortcut clicked", async () => {
    const { toast } = await import("sonner");
    const user = userEvent.setup();
    renderAt();
    await user.click(screen.getByTestId("shortcut-mail"));
    expect(await screen.findByTestId("modal-mail")).toBeInTheDocument();
    expect(toast.info).toHaveBeenCalledWith(
      expect.stringContaining("Step 2"),
      expect.anything(),
    );
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
