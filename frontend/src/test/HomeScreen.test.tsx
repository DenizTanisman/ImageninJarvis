import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HomeScreen } from "@/screens/HomeScreen";

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="current-path">{location.pathname}</div>;
}

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HomeScreen />} />
        <Route path="/voice" element={<LocationProbe />} />
        <Route path="/chat" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("HomeScreen", () => {
  it("renders bot avatar and both nav buttons", () => {
    renderWithRouter();
    expect(screen.getByRole("img", { name: /Jarvis bot avatar/i })).toBeInTheDocument();
    expect(screen.getByTestId("nav-voice")).toBeInTheDocument();
    expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
  });

  it("navigates to /voice when voice button clicked", async () => {
    const user = userEvent.setup();
    renderWithRouter();
    await user.click(screen.getByTestId("nav-voice"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/voice");
  });

  it("navigates to /chat when chat button clicked", async () => {
    const user = userEvent.setup();
    renderWithRouter();
    await user.click(screen.getByTestId("nav-chat"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/chat");
  });
});
