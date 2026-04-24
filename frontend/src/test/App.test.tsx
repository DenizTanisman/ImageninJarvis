import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("App", () => {
  it("renders step 0.1 placeholder", () => {
    render(<App />);
    expect(screen.getByText(/Step 0\.1 OK/)).toBeInTheDocument();
  });
});
