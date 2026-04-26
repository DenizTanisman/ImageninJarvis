import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MailCard } from "@/components/capability/MailCard";
import { useMailUI } from "@/store/mail";

const fetchMailSummaryMock = vi.fn();
const getAuthStatusMock = vi.fn();

vi.mock("@/api/client", () => ({
  fetchMailSummary: (...args: unknown[]) => fetchMailSummaryMock(...args),
  getAuthStatus: (...args: unknown[]) => getAuthStatusMock(...args),
  googleConnectUrl: () => "http://localhost:8000/auth/google/start",
  ChatNetworkError: class extends Error {},
}));

beforeEach(() => {
  useMailUI.getState().reset();
  fetchMailSummaryMock.mockReset();
  getAuthStatusMock.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

const fakePayload = {
  range: { kind: "daily", after: "2026-04-24", before: "2026-04-25" },
  categories: {
    important: [
      {
        id: "m1",
        from: "boss@example.com",
        subject: "Acil",
        snippet: "Yarın için hazır mıyız?",
        summary: "Yarınki sunum kontrolü",
        needs_reply: true,
        confidence: 0.95,
      },
    ],
    dm: [],
    promo: [
      {
        id: "m2",
        from: "shop@example.com",
        subject: "Kampanya",
        snippet: "İndirim devam",
        summary: "Hafta sonu indirim",
        needs_reply: false,
        confidence: 0.9,
      },
    ],
    other: [],
  },
  needs_reply_count: 1,
  total: 2,
};

describe("MailCard real-data flow", () => {
  it("shows a Connect Google block when not authenticated", async () => {
    getAuthStatusMock.mockResolvedValueOnce({ connected: false, scopes: [], can_send: false });
    render(<MailCard />);
    expect(await screen.findByTestId("mail-needs-auth")).toBeInTheDocument();
    expect(screen.getByTestId("connect-google")).toHaveAttribute(
      "href",
      "http://localhost:8000/auth/google/start",
    );
    expect(fetchMailSummaryMock).not.toHaveBeenCalled();
  });

  it("renders summary buckets after a successful fetch", async () => {
    getAuthStatusMock.mockResolvedValue({
      connected: true,
      scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
      can_send: false,
    });
    fetchMailSummaryMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "MailCard",
      data: fakePayload,
      meta: { source: "live" },
    });

    render(<MailCard />);
    expect(await screen.findByTestId("mail-cat-important")).toBeInTheDocument();
    expect(screen.getByText("boss@example.com")).toBeInTheDocument();
    expect(screen.getByText("Acil")).toBeInTheDocument();
    expect(screen.getByTestId("mail-reply-prompt").textContent).toContain("1");
  });

  it("re-fetches when range kind changes", async () => {
    getAuthStatusMock.mockResolvedValue({ connected: true, scopes: [], can_send: false });
    fetchMailSummaryMock.mockResolvedValue({
      ok: true,
      ui_type: "MailCard",
      data: fakePayload,
      meta: { source: "live" },
    });

    const user = userEvent.setup();
    render(<MailCard />);
    await screen.findByTestId("mail-cat-important");
    expect(fetchMailSummaryMock).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("range-weekly"));
    await waitFor(() => expect(fetchMailSummaryMock).toHaveBeenCalledTimes(2));
    const lastCallArg = fetchMailSummaryMock.mock.calls[1][0] as {
      range_kind: string;
    };
    expect(lastCallArg.range_kind).toBe("weekly");
  });

  it("renders friendly error when backend returns ok:false", async () => {
    getAuthStatusMock.mockResolvedValueOnce({ connected: true, scopes: [], can_send: false });
    fetchMailSummaryMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Mailler çekilemedi", retry_after: 10 },
    });
    render(<MailCard />);
    expect(await screen.findByTestId("mail-error")).toHaveTextContent(
      /çekilemedi/,
    );
  });

  it("renders error when network call throws", async () => {
    getAuthStatusMock.mockRejectedValueOnce(new Error("backend down"));
    render(<MailCard />);
    expect(await screen.findByTestId("mail-error")).toBeInTheDocument();
  });

  it("calls onReplyClick when prompt button is pressed", async () => {
    getAuthStatusMock.mockResolvedValueOnce({ connected: true, scopes: [], can_send: false });
    fetchMailSummaryMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "MailCard",
      data: fakePayload,
      meta: { source: "live" },
    });
    const onReply = vi.fn();
    const user = userEvent.setup();
    render(<MailCard onReplyClick={onReply} />);
    await user.click(await screen.findByTestId("mail-reply-prompt"));
    expect(onReply).toHaveBeenCalledOnce();
  });
});
