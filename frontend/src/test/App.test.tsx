import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("App router", () => {
  it("renders HomeScreen on root path", () => {
    render(<App />);
    expect(screen.getByRole("img", { name: /Jarvis bot avatar/i })).toBeInTheDocument();
    expect(screen.getByTestId("nav-voice")).toBeInTheDocument();
    expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
  });
});
