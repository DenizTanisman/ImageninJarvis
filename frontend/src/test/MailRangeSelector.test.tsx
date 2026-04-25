import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { MailRangeSelector } from "@/components/capability/MailRangeSelector";
import { resolveRangeBounds, useMailUI } from "@/store/mail";

beforeEach(() => {
  useMailUI.getState().reset();
});

describe("MailRangeSelector", () => {
  it("defaults to daily and hides custom date inputs", () => {
    render(<MailRangeSelector />);
    expect(useMailUI.getState().range.kind).toBe("daily");
    expect(screen.getByTestId("range-daily").className).toMatch(/bg-sky-500/);
    expect(screen.queryByTestId("custom-range-fields")).toBeNull();
  });

  it("switches to weekly and updates store", async () => {
    const user = userEvent.setup();
    render(<MailRangeSelector />);
    await user.click(screen.getByTestId("range-weekly"));
    expect(useMailUI.getState().range.kind).toBe("weekly");
  });

  it("switches to custom and reveals date inputs bound to the store", async () => {
    const user = userEvent.setup();
    render(<MailRangeSelector />);
    await user.click(screen.getByTestId("range-custom"));
    expect(screen.getByTestId("custom-range-fields")).toBeInTheDocument();

    const after = screen.getByTestId("range-custom-after") as HTMLInputElement;
    const before = screen.getByTestId("range-custom-before") as HTMLInputElement;

    await user.clear(after);
    await user.type(after, "2026-04-01");
    await user.clear(before);
    await user.type(before, "2026-04-15");

    const range = useMailUI.getState().range;
    expect(range.customAfter).toBe("2026-04-01");
    expect(range.customBefore).toBe("2026-04-15");
  });
});

describe("resolveRangeBounds", () => {
  it("returns 1-day window for daily", () => {
    const { after, before } = resolveRangeBounds({
      kind: "daily",
      customAfter: "x",
      customBefore: "y",
    });
    const a = new Date(after);
    const b = new Date(before);
    const diffDays = (b.getTime() - a.getTime()) / 86_400_000;
    expect(diffDays).toBeCloseTo(1, 0);
  });

  it("returns 7-day window for weekly", () => {
    const { after, before } = resolveRangeBounds({
      kind: "weekly",
      customAfter: "x",
      customBefore: "y",
    });
    const diffDays =
      (new Date(before).getTime() - new Date(after).getTime()) / 86_400_000;
    expect(diffDays).toBeCloseTo(7, 0);
  });

  it("returns custom bounds for custom kind", () => {
    expect(
      resolveRangeBounds({
        kind: "custom",
        customAfter: "2026-04-01",
        customBefore: "2026-04-30",
      }),
    ).toEqual({ after: "2026-04-01", before: "2026-04-30" });
  });
});
