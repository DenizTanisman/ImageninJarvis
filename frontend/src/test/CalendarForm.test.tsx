import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarForm } from "@/components/capability/CalendarForm";

const callCalendarMock = vi.fn();

vi.mock("@/api/client", () => ({
  callCalendar: (...args: unknown[]) => callCalendarMock(...args),
  ChatNetworkError: class extends Error {},
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

beforeEach(() => callCalendarMock.mockReset());
afterEach(() => {
  vi.clearAllMocks();
});

describe("CalendarForm", () => {
  it("disables submit until title + date + start + end are filled", async () => {
    const user = userEvent.setup();
    render(<CalendarForm />);
    const submit = screen.getByTestId("calendar-submit");
    expect(submit).toBeDisabled();

    await user.type(screen.getByTestId("field-title"), "Sunum");
    await user.type(screen.getByTestId("field-date"), "2026-05-01");
    await user.type(screen.getByTestId("field-start"), "10:00");
    await user.type(screen.getByTestId("field-end"), "11:00");
    expect(submit).toBeEnabled();
  });

  it("blocks submit when end <= start and shows a warning", async () => {
    const user = userEvent.setup();
    render(<CalendarForm />);
    await user.type(screen.getByTestId("field-title"), "x");
    await user.type(screen.getByTestId("field-date"), "2026-05-01");
    await user.type(screen.getByTestId("field-start"), "11:00");
    await user.type(screen.getByTestId("field-end"), "10:00");
    expect(screen.getByTestId("form-time-warning")).toBeInTheDocument();
    expect(screen.getByTestId("calendar-submit")).toBeDisabled();
  });

  it("submits ISO timestamps and calls onCreated on success", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "CalendarEvent",
      data: {
        id: "e1",
        summary: "Sunum",
        start: "2026-05-01T10:00:00+03:00",
        end: "2026-05-01T11:00:00+03:00",
        description: "Q2",
        html_link: "",
      },
    });
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(<CalendarForm onCreated={onCreated} />);
    await user.type(screen.getByTestId("field-title"), "Sunum");
    await user.type(screen.getByTestId("field-date"), "2026-05-01");
    await user.type(screen.getByTestId("field-start"), "10:00");
    await user.type(screen.getByTestId("field-end"), "11:00");
    await user.type(screen.getByTestId("field-detail"), "Q2");
    await user.click(screen.getByTestId("calendar-submit"));

    await waitFor(() =>
      expect(callCalendarMock).toHaveBeenCalledWith({
        action: "create",
        summary: "Sunum",
        start: "2026-05-01T10:00:00+03:00",
        end: "2026-05-01T11:00:00+03:00",
        description: "Q2",
      }),
    );
    expect(onCreated).toHaveBeenCalledWith(
      expect.objectContaining({ id: "e1" }),
    );
  });

  it("renders friendly error when backend returns ok:false", async () => {
    callCalendarMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Takvim izni yok.", retry_after: null },
    });
    const user = userEvent.setup();
    render(<CalendarForm />);
    await user.type(screen.getByTestId("field-title"), "x");
    await user.type(screen.getByTestId("field-date"), "2026-05-01");
    await user.type(screen.getByTestId("field-start"), "10:00");
    await user.type(screen.getByTestId("field-end"), "11:00");
    await user.click(screen.getByTestId("calendar-submit"));
    expect(await screen.findByTestId("form-error")).toHaveTextContent(
      /takvim izni/i,
    );
  });
});
