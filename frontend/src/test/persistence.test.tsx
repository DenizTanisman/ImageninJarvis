import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import { useConversation } from "@/store/conversation";
import { useMode } from "@/store/mode";

vi.mock("@/api/client", () => ({
  sendChat: vi.fn().mockResolvedValue({
    ok: true,
    ui_type: "text",
    data: "echo",
  }),
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
});

describe("mode-agnostic persistence", () => {
  it("preserves chat history across chat → voice → chat navigation", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByTestId("nav-chat"));
    expect(useMode.getState().mode).toBe("chat");

    const input = screen.getByTestId("chat-input");
    await user.type(input, "ilk mesaj");
    await user.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(
        within(screen.getByTestId("message-list")).getByText("ilk mesaj"),
      ).toBeInTheDocument(),
    );
    await user.type(input, "ikinci mesaj");
    await user.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(
        within(screen.getByTestId("message-list")).getByText("ikinci mesaj"),
      ).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("voice-toggle"));
    expect(useMode.getState().mode).toBe("voice");
    // greeting + (user1 + assistant1) + (user2 + assistant2) = 5
    expect(screen.getByTestId("voice-msg-count")).toHaveTextContent(
      /5 mesaj/,
    );

    await user.click(screen.getByTestId("switch-to-chat"));
    expect(useMode.getState().mode).toBe("chat");

    const list = screen.getByTestId("message-list");
    expect(within(list).getByText("ilk mesaj")).toBeInTheDocument();
    expect(within(list).getByText("ikinci mesaj")).toBeInTheDocument();
    expect(
      within(list).getByText(/nasıl yardımcı olabilirim/i),
    ).toBeInTheDocument();
  });
});
