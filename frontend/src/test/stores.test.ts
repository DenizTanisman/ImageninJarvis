import { beforeEach, describe, expect, it } from "vitest";

import { useConversation } from "@/store/conversation";
import { deriveModeFromPath, useMode } from "@/store/mode";

beforeEach(() => {
  useConversation.getState().resetToGreeting();
  useMode.setState({ mode: "home" });
});

describe("conversation store", () => {
  it("starts with a single assistant greeting", () => {
    const { messages } = useConversation.getState();
    expect(messages).toHaveLength(1);
    expect(messages[0].role).toBe("assistant");
  });

  it("appends messages via addMessage and returns the created message", () => {
    const store = useConversation.getState();
    const added = store.addMessage("user", "Selam");
    const { messages } = useConversation.getState();
    expect(messages).toHaveLength(2);
    expect(messages[1]).toMatchObject({ role: "user", text: "Selam" });
    expect(added.id).toBe(messages[1].id);
  });

  it("clearMessages empties the list; resetToGreeting restores it", () => {
    useConversation.getState().addMessage("user", "ilk");
    useConversation.getState().clearMessages();
    expect(useConversation.getState().messages).toHaveLength(0);
    useConversation.getState().resetToGreeting();
    expect(useConversation.getState().messages).toHaveLength(1);
  });
});

describe("mode store", () => {
  it("defaults to home and updates via setMode", () => {
    expect(useMode.getState().mode).toBe("home");
    useMode.getState().setMode("voice");
    expect(useMode.getState().mode).toBe("voice");
  });

  it("derives mode from URL path", () => {
    expect(deriveModeFromPath("/")).toBe("home");
    expect(deriveModeFromPath("/voice")).toBe("voice");
    expect(deriveModeFromPath("/chat")).toBe("chat");
    expect(deriveModeFromPath("/chat/thread/123")).toBe("chat");
  });
});
