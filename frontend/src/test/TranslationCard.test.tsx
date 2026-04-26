import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TranslationCard } from "@/components/capability/TranslationCard";

const translateMock = vi.fn();

vi.mock("@/api/client", () => ({
  translate: (...args: unknown[]) => translateMock(...args),
  ChatNetworkError: class extends Error {},
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}));

beforeEach(() => {
  translateMock.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("TranslationCard real-API flow", () => {
  it("disables translate when source is empty", () => {
    render(<TranslationCard />);
    expect(screen.getByTestId("translate-button")).toBeDisabled();
  });

  it("posts the source to the API and renders translated_text", async () => {
    translateMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "TranslationCard",
      data: {
        source_text: "merhaba",
        translated_text: "hello",
        source_lang: "tr",
        target_lang: "en",
      },
    });
    const user = userEvent.setup();
    render(<TranslationCard />);
    await user.type(screen.getByTestId("source-pane"), "merhaba");
    await user.click(screen.getByTestId("translate-button"));
    await waitFor(() =>
      expect(translateMock).toHaveBeenCalledWith(
        expect.objectContaining({ text: "merhaba", target: "en", source: "auto" }),
      ),
    );
    const target = await screen.findByTestId("target-pane");
    await waitFor(() => expect((target as HTMLTextAreaElement).value).toBe("hello"));
  });

  it("renders friendly error when backend returns ok:false", async () => {
    translateMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Çeviri servisi yanıt vermiyor.", retry_after: 15 },
    });
    const user = userEvent.setup();
    render(<TranslationCard />);
    await user.type(screen.getByTestId("source-pane"), "hello");
    await user.click(screen.getByTestId("translate-button"));
    expect(await screen.findByTestId("translation-error")).toHaveTextContent(
      /yanıt vermiyor/,
    );
  });

  it("swap moves text between panes and avoids using auto as a target", async () => {
    const user = userEvent.setup();
    render(<TranslationCard />);
    await user.type(screen.getByTestId("source-pane"), "merhaba");
    // default langs: source=auto, target=en. After swap target was "auto"
    // which is invalid; the component should pick a sensible source instead.
    await user.click(screen.getByTestId("swap-button"));
    const sourceLang = screen.getByTestId("lang-source") as HTMLSelectElement;
    const targetLang = screen.getByTestId("lang-target") as HTMLSelectElement;
    expect(sourceLang.value).toBe("en");
    expect(targetLang).not.toHaveValue("auto");
  });

  it("source pane has 'auto' option, target does not", () => {
    render(<TranslationCard />);
    const sourceOptions = Array.from(
      (screen.getByTestId("lang-source") as HTMLSelectElement).options,
    ).map((o) => o.value);
    const targetOptions = Array.from(
      (screen.getByTestId("lang-target") as HTMLSelectElement).options,
    ).map((o) => o.value);
    expect(sourceOptions).toContain("auto");
    expect(targetOptions).not.toContain("auto");
  });

  it("changing target language picker updates the request payload", async () => {
    translateMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "TranslationCard",
      data: { source_text: "hello", translated_text: "Hallo", source_lang: "auto", target_lang: "de" },
    });
    const user = userEvent.setup();
    render(<TranslationCard />);
    await user.type(screen.getByTestId("source-pane"), "hello");
    await user.selectOptions(screen.getByTestId("lang-target"), "de");
    await user.click(screen.getByTestId("translate-button"));
    await waitFor(() =>
      expect(translateMock).toHaveBeenCalledWith(
        expect.objectContaining({ target: "de" }),
      ),
    );
  });
});
