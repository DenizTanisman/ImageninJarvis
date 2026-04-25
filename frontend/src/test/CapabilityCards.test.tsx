import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarForm } from "@/components/capability/CalendarForm";
import { DocumentCard } from "@/components/capability/DocumentCard";
import { EventList } from "@/components/capability/EventList";
import { MailCard } from "@/components/capability/MailCard";
import { TranslationCard } from "@/components/capability/TranslationCard";
import { MOCK_EVENTS, MOCK_MAILS, MOCK_TRANSLATION } from "@/lib/mock-data";

describe("MailCard", () => {
  it("renders four categories and the needs-reply prompt", () => {
    const onReply = vi.fn();
    render(<MailCard onReplyClick={onReply} />);
    (["important", "dm", "promo", "other"] as const).forEach((key) => {
      expect(screen.getByTestId(`mail-cat-${key}`)).toBeInTheDocument();
    });
    const needsReplyCount = Object.values(MOCK_MAILS)
      .flat()
      .filter((m) => m.needsReply).length;
    expect(
      screen.getByTestId("mail-reply-prompt").textContent,
    ).toContain(String(needsReplyCount));
  });

  it("fires onReplyClick when prompt clicked", async () => {
    const onReply = vi.fn();
    const user = userEvent.setup();
    render(<MailCard onReplyClick={onReply} />);
    await user.click(screen.getByTestId("mail-reply-prompt"));
    expect(onReply).toHaveBeenCalledOnce();
  });
});

describe("TranslationCard", () => {
  it("swaps source and target content and languages", async () => {
    const user = userEvent.setup();
    render(<TranslationCard />);
    const source = screen.getByTestId("source-pane") as HTMLTextAreaElement;
    const target = screen.getByTestId("target-pane") as HTMLTextAreaElement;
    expect(source.value).toBe(MOCK_TRANSLATION.source);
    expect(target.value).toBe(MOCK_TRANSLATION.target);
    await user.click(screen.getByTestId("swap-button"));
    expect(source.value).toBe(MOCK_TRANSLATION.target);
    expect(target.value).toBe(MOCK_TRANSLATION.source);
  });
});

describe("CalendarForm", () => {
  it("disables submit until required fields are filled, then submits", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CalendarForm onSubmit={onSubmit} />);
    const submit = screen.getByTestId("calendar-submit");
    expect(submit).toBeDisabled();
    await user.type(screen.getByTestId("field-title"), "Sunum");
    await user.type(screen.getByTestId("field-date"), "2026-05-01");
    await user.type(screen.getByTestId("field-time"), "10:00");
    expect(submit).toBeEnabled();
    await user.click(submit);
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Sunum", date: "2026-05-01", time: "10:00" }),
    );
  });
});

describe("EventList", () => {
  it("renders all mock events", () => {
    render(<EventList />);
    const list = screen.getByTestId("event-list");
    MOCK_EVENTS.forEach((event) => {
      expect(within(list).getByText(event.title)).toBeInTheDocument();
    });
  });
});

describe("DocumentCard", () => {
  it("toggles between Drive list and Upload zone", async () => {
    const user = userEvent.setup();
    render(<DocumentCard />);
    expect(screen.getByTestId("drive-list")).toBeInTheDocument();
    await user.click(screen.getByTestId("tab-upload"));
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.queryByTestId("drive-list")).toBeNull();
    await user.click(screen.getByTestId("tab-drive"));
    expect(screen.getByTestId("drive-list")).toBeInTheDocument();
  });
});
