import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DocumentCard } from "@/components/capability/DocumentCard";

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
