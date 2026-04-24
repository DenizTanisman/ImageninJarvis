import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { VoiceScreen } from "@/screens/VoiceScreen";

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
  },
  Toaster: () => null,
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="current-path">{location.pathname}</div>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<LocationProbe />} />
        <Route path="/voice" element={<VoiceScreen />} />
        <Route path="/chat" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VoiceScreen", () => {
  it("renders pulsing bot avatar and listening label", () => {
    renderAt("/voice");
    expect(screen.getByRole("img", { name: /Jarvis bot avatar/i })).toBeInTheDocument();
    expect(screen.getByText(/Dinleniyor/i)).toBeInTheDocument();
  });

  it("navigates back to home when back button clicked", async () => {
    const user = userEvent.setup();
    renderAt("/voice");
    await user.click(screen.getByTestId("back-home"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/");
  });

  it("fires toast and navigates to /chat when switch button clicked", async () => {
    const { toast } = await import("sonner");
    const user = userEvent.setup();
    renderAt("/voice");
    await user.click(screen.getByTestId("switch-to-chat"));
    expect(toast.info).toHaveBeenCalledWith(
      expect.stringContaining("Step 1"),
      expect.anything(),
    );
    expect(screen.getByTestId("current-path")).toHaveTextContent("/chat");
  });
});
