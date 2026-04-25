import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatNetworkError, sendChat } from "@/api/client";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function mockFetch(response: Response | Promise<Response>) {
  globalThis.fetch = vi.fn(() => Promise.resolve(response)) as typeof fetch;
}

describe("sendChat", () => {
  it("posts to /chat and returns parsed success body", async () => {
    mockFetch(
      new Response(
        JSON.stringify({ ok: true, ui_type: "text", data: "Merhaba" }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    const result = await sendChat("Selam");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data).toBe("Merhaba");
    }
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/chat"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "Selam" }),
      }),
    );
  });

  it("returns parsed error body when ok=false", async () => {
    mockFetch(
      new Response(
        JSON.stringify({
          ok: false,
          error: { user_message: "tekrar dener misin", retry_after: 10 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    const result = await sendChat("hi");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.user_message).toMatch(/tekrar/);
    }
  });

  it("throws ChatNetworkError when fetch rejects", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.reject(new TypeError("network down")),
    ) as typeof fetch;
    await expect(sendChat("hi")).rejects.toBeInstanceOf(ChatNetworkError);
  });

  it("throws ChatNetworkError on 5xx", async () => {
    mockFetch(new Response("oops", { status: 500 }));
    await expect(sendChat("hi")).rejects.toBeInstanceOf(ChatNetworkError);
  });
});
