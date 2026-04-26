import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BatchReplyView } from "@/components/capability/BatchReplyView";
import type { AuthStatus, MailSummaryData } from "@/api/client";

const generateDraftsMock = vi.fn();
const sendDraftMock = vi.fn();

vi.mock("@/api/client", () => ({
  generateDrafts: (...args: unknown[]) => generateDraftsMock(...args),
  sendDraft: (...args: unknown[]) => sendDraftMock(...args),
  googleConnectUrl: () => "http://localhost:8000/auth/google/start",
  ChatNetworkError: class extends Error {},
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}));

const baseAuth: AuthStatus = {
  connected: true,
  scopes: [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
  ],
  can_send: true,
};

const baseSummary: MailSummaryData = {
  range: { kind: "daily", after: "2026-04-24", before: "2026-04-25" },
  categories: {
    important: [
      {
        id: "m1",
        from: "alice@example.com",
        subject: "Acil",
        snippet: "Yarın",
        summary: "Yarınki sunum",
        needs_reply: true,
        confidence: 0.95,
      },
      {
        id: "m2",
        from: "bob@example.com",
        subject: "Bilgi",
        snippet: "...",
        summary: "Görev güncellemesi",
        needs_reply: true,
        confidence: 0.9,
      },
    ],
    dm: [],
    promo: [
      {
        id: "m3",
        from: "shop@example.com",
        subject: "Kampanya",
        snippet: "...",
        summary: "İndirim",
        needs_reply: false,
        confidence: 0.92,
      },
    ],
    other: [],
  },
  needs_reply_count: 2,
  total: 3,
};

beforeEach(() => {
  generateDraftsMock.mockReset();
  sendDraftMock.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("BatchReplyView", () => {
  it("shows reconnect prompt when can_send is false", () => {
    render(
      <BatchReplyView
        summary={baseSummary}
        authStatus={{ ...baseAuth, can_send: false }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("reply-needs-send-scope")).toBeInTheDocument();
    expect(screen.getByTestId("reply-reconnect")).toHaveAttribute(
      "href",
      "http://localhost:8000/auth/google/start",
    );
  });

  it("lists only needs-reply mails with checkboxes pre-selected", () => {
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={vi.fn()} />);
    expect(screen.getByTestId("reply-candidate-m1")).toBeInTheDocument();
    expect(screen.getByTestId("reply-candidate-m2")).toBeInTheDocument();
    expect(screen.queryByTestId("reply-candidate-m3")).toBeNull();
    expect(
      (screen.getByTestId("reply-toggle-m1") as HTMLInputElement).checked,
    ).toBe(true);
  });

  it("shows a 'no mails' message when nothing needs reply", () => {
    const empty: MailSummaryData = {
      ...baseSummary,
      categories: {
        important: [],
        dm: [],
        promo: [],
        other: [],
      },
      needs_reply_count: 0,
    };
    render(<BatchReplyView summary={empty} authStatus={baseAuth} onClose={vi.fn()} />);
    expect(screen.getByText(/yanıt bekleyen mail yok/i)).toBeInTheDocument();
  });

  it("requests drafts for selected ids and shows review step", async () => {
    generateDraftsMock.mockResolvedValueOnce({
      drafts: [
        { message_id: "m1", thread_id: "t1", to: "alice@example.com", subject: "Acil", body: "Cevap 1" },
        { message_id: "m2", thread_id: "t2", to: "bob@example.com", subject: "Bilgi", body: "Cevap 2" },
      ],
      failures: [],
    });
    const user = userEvent.setup();
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={vi.fn()} />);
    await user.click(screen.getByTestId("reply-continue"));
    expect(generateDraftsMock).toHaveBeenCalledWith(["m1", "m2"]);
    expect(await screen.findByTestId("reply-draft-m1")).toBeInTheDocument();
    expect(screen.getByTestId("reply-draft-m2")).toBeInTheDocument();
  });

  it("approves a draft → calls sendDraft and marks it sent", async () => {
    generateDraftsMock.mockResolvedValueOnce({
      drafts: [
        { message_id: "m1", thread_id: "t1", to: "alice@example.com", subject: "Acil", body: "Hi" },
        { message_id: "m2", thread_id: "t2", to: "bob@example.com", subject: "Bilgi", body: "Hi" },
      ],
      failures: [],
    });
    sendDraftMock.mockResolvedValueOnce({ sent_message_id: "sent-1", error: null });
    const user = userEvent.setup();
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={vi.fn()} />);
    await user.click(screen.getByTestId("reply-continue"));
    await screen.findByTestId("reply-draft-m1");

    await user.click(screen.getByTestId("reply-approve-m1"));
    await waitFor(() =>
      expect(sendDraftMock).toHaveBeenCalledWith(
        expect.objectContaining({ message_id: "m1", to: "alice@example.com" }),
      ),
    );
  });

  it("skipping a draft does not send", async () => {
    generateDraftsMock.mockResolvedValueOnce({
      drafts: [
        { message_id: "m1", thread_id: "t1", to: "x@y.com", subject: "s", body: "b" },
      ],
      failures: [],
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={onClose} />);
    await user.click(screen.getByTestId("reply-continue"));
    await screen.findByTestId("reply-draft-m1");
    await user.click(screen.getByTestId("reply-skip-m1"));
    expect(sendDraftMock).not.toHaveBeenCalled();
  });

  it("editing the body changes what gets sent", async () => {
    generateDraftsMock.mockResolvedValueOnce({
      drafts: [
        { message_id: "m1", thread_id: "t1", to: "x@y.com", subject: "s", body: "old" },
      ],
      failures: [],
    });
    sendDraftMock.mockResolvedValueOnce({ sent_message_id: "sent", error: null });
    const user = userEvent.setup();
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={vi.fn()} />);
    await user.click(screen.getByTestId("reply-continue"));
    const textarea = await screen.findByTestId("reply-body-m1");
    await user.clear(textarea);
    await user.type(textarea, "edited reply");
    await user.click(screen.getByTestId("reply-approve-m1"));
    await waitFor(() =>
      expect(sendDraftMock).toHaveBeenCalledWith(
        expect.objectContaining({ body: "edited reply" }),
      ),
    );
  });

  it("shows error message when no drafts could be generated", async () => {
    generateDraftsMock.mockResolvedValueOnce({ drafts: [], failures: ["m1", "m2"] });
    const user = userEvent.setup();
    render(<BatchReplyView summary={baseSummary} authStatus={baseAuth} onClose={vi.fn()} />);
    await user.click(screen.getByTestId("reply-continue"));
    expect(await screen.findByTestId("reply-error")).toHaveTextContent(
      /üretilemedi/i,
    );
  });
});
