import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EventList } from "@/components/capability/EventList";

const callCalendarMock = vi.fn();

vi.mock("@/api/client", () => ({
  callCalendar: (...args: unknown[]) => callCalendarMock(...args),
  ChatNetworkError: class extends Error {},
  googleConnectUrl: () => "http://localhost:8000/auth/google/start",
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

const fakeEvents = [
  {
    id: "e1",
    summary: "Sunum",
    start: "2026-04-28T14:00:00+03:00",
    end: "2026-04-28T15:00:00+03:00",
    description: "Q2 sprint",
    html_link: "",
  },
  {
    id: "e2",
    summary: "Sample Project sync",
    start: "2026-04-29T10:00:00+03:00",
    end: "2026-04-29T10:30:00+03:00",
    description: "Haftalık güncelleme",
    html_link: "",
  },
];

beforeEach(() => callCalendarMock.mockReset());
afterEach(() => vi.clearAllMocks());

describe("EventList real-data flow", () => {
  it("loads events on mount and renders them", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "EventList",
      data: { events: fakeEvents, days: 7 },
    });
    render(<EventList />);
    expect(await screen.findByTestId("event-e1")).toBeInTheDocument();
    expect(screen.getByText("Sunum")).toBeInTheDocument();
    expect(screen.getByText("Sample Project sync")).toBeInTheDocument();
  });

  it("shows reconnect prompt when backend signals missing scope", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Takvim izni yok.", retry_after: null },
    });
    render(<EventList />);
    expect(await screen.findByTestId("events-needs-auth")).toHaveTextContent(
      /takvim izni/i,
    );
  });

  it("shows generic error when backend signals other failure", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Takvim isteği başarısız oldu.", retry_after: 10 },
    });
    render(<EventList />);
    expect(await screen.findByTestId("events-error")).toHaveTextContent(
      /başarısız/i,
    );
  });

  it("shows empty-state when there are no events in the window", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "EventList",
      data: { events: [], days: 7 },
    });
    render(<EventList />);
    expect(await screen.findByText(/etkinlik yok/i)).toBeInTheDocument();
  });

  it("delete button opens confirm dialog and only sends after confirm", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "EventList",
      data: { events: [fakeEvents[0]], days: 7 },
    });
    const user = userEvent.setup();
    render(<EventList />);
    await screen.findByTestId("event-e1");
    await user.click(screen.getByTestId("event-delete-e1"));
    expect(screen.getByTestId("event-confirm-delete")).toBeInTheDocument();
    // Cancel keeps things as-is
    await user.click(screen.getByTestId("event-confirm-cancel"));
    // After cancel only the initial list call exists
    expect(callCalendarMock).toHaveBeenCalledTimes(1);
  });

  it("confirming delete posts the delete payload and refreshes list", async () => {
    callCalendarMock
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "EventList",
        data: { events: [fakeEvents[0]], days: 7 },
      })
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "text",
        data: { event_id: "e1" },
        meta: { action: "delete" },
      })
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "EventList",
        data: { events: [], days: 7 },
      });
    const user = userEvent.setup();
    render(<EventList />);
    await screen.findByTestId("event-e1");
    await user.click(screen.getByTestId("event-delete-e1"));
    await user.click(screen.getByTestId("event-confirm-yes"));
    await waitFor(() =>
      expect(callCalendarMock).toHaveBeenCalledWith({
        action: "delete",
        event_id: "e1",
      }),
    );
  });

  it("edit dialog patches summary + description", async () => {
    callCalendarMock
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "EventList",
        data: { events: [fakeEvents[0]], days: 7 },
      })
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "CalendarEvent",
        data: { ...fakeEvents[0], summary: "Yeni başlık" },
        meta: { action: "update" },
      })
      .mockResolvedValueOnce({
        ok: true,
        ui_type: "EventList",
        data: { events: [{ ...fakeEvents[0], summary: "Yeni başlık" }], days: 7 },
      });
    const user = userEvent.setup();
    render(<EventList />);
    await screen.findByTestId("event-e1");
    await user.click(screen.getByTestId("event-edit-e1"));
    const titleInput = screen.getByTestId("edit-title") as HTMLInputElement;
    await user.clear(titleInput);
    await user.type(titleInput, "Yeni başlık");
    await user.click(screen.getByTestId("edit-save"));
    await waitFor(() =>
      expect(callCalendarMock).toHaveBeenCalledWith(
        expect.objectContaining({
          action: "update",
          event_id: "e1",
          summary: "Yeni başlık",
        }),
      ),
    );
  });
});
