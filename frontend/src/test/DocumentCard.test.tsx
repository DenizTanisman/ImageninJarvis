import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DocumentCard } from "@/components/capability/DocumentCard";

const uploadDocumentMock = vi.fn();
const listDriveFilesMock = vi.fn();
const importDriveFileMock = vi.fn();
const askDocumentMock = vi.fn();

vi.mock("@/api/client", () => {
  class ChatNetworkError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "ChatNetworkError";
    }
  }
  return {
    uploadDocument: (...args: unknown[]) => uploadDocumentMock(...args),
    listDriveFiles: (...args: unknown[]) => listDriveFilesMock(...args),
    importDriveFile: (...args: unknown[]) => importDriveFileMock(...args),
    askDocument: (...args: unknown[]) => askDocumentMock(...args),
    googleConnectUrl: () => "http://localhost:8000/auth/google/start",
    ChatNetworkError,
  };
});

async function importChatNetworkError() {
  const mod = await import("@/api/client");
  return mod.ChatNetworkError;
}

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

beforeEach(() => {
  uploadDocumentMock.mockReset();
  listDriveFilesMock.mockReset();
  importDriveFileMock.mockReset();
  askDocumentMock.mockReset();
});

afterEach(() => vi.clearAllMocks());

const fakeDoc = {
  doc_id: "doc-1",
  page_count: 3,
  original_name: "plan.pdf",
  mime_type: "application/pdf",
  size_bytes: 4096,
};

describe("DocumentCard tabs", () => {
  it("starts on the Upload tab and exposes the dropzone", () => {
    render(<DocumentCard />);
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.queryByTestId("drive-list")).toBeNull();
  });

  it("switches to Drive tab and triggers listDriveFiles", async () => {
    listDriveFilesMock.mockResolvedValueOnce([
      {
        id: "f1",
        name: "notes.txt",
        mime_type: "text/plain",
        size_bytes: 100,
        modified_time: "2026-04-25T10:00:00Z",
      },
    ]);
    const user = userEvent.setup();
    render(<DocumentCard />);
    await user.click(screen.getByTestId("tab-drive"));
    expect(await screen.findByTestId("drive-pick-f1")).toBeInTheDocument();
  });
});

describe("DocumentCard upload flow", () => {
  it("uploads a file and switches to ready state", async () => {
    uploadDocumentMock.mockResolvedValueOnce(fakeDoc);
    const user = userEvent.setup();
    render(<DocumentCard />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = new File(["hello"], "plan.pdf", { type: "application/pdf" });
    await user.upload(input, file);
    expect(await screen.findByTestId("document-ready")).toBeInTheDocument();
    expect(screen.getByText("plan.pdf")).toBeInTheDocument();
    expect(screen.getByText(/3 sayfa/)).toBeInTheDocument();
  });

  it("shows error when upload fails", async () => {
    const ChatNetworkError = await importChatNetworkError();
    uploadDocumentMock.mockImplementationOnce(
      () => Promise.reject(new ChatNetworkError("Dosya çok büyük")),
    );
    const user = userEvent.setup();
    render(<DocumentCard />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = new File(["x"], "huge.pdf", { type: "application/pdf" });
    await user.upload(input, file);
    await waitFor(
      () => expect(screen.getByTestId("doc-error")).toBeInTheDocument(),
      { timeout: 2000 },
    );
  });
});

describe("DocumentCard Drive flow", () => {
  it("imports the picked Drive file and switches to ready state", async () => {
    listDriveFilesMock.mockResolvedValueOnce([
      {
        id: "f1",
        name: "drive-notes.pdf",
        mime_type: "application/pdf",
        size_bytes: 200,
        modified_time: "",
      },
    ]);
    importDriveFileMock.mockResolvedValueOnce({
      ...fakeDoc,
      original_name: "drive-notes.pdf",
    });
    const user = userEvent.setup();
    render(<DocumentCard />);
    await user.click(screen.getByTestId("tab-drive"));
    await screen.findByTestId("drive-pick-f1");
    await user.click(screen.getByTestId("drive-pick-f1"));
    expect(await screen.findByTestId("document-ready")).toBeInTheDocument();
    expect(screen.getByText("drive-notes.pdf")).toBeInTheDocument();
  });

  it("shows reconnect prompt when listDriveFiles signals auth failure", async () => {
    const ChatNetworkError = await importChatNetworkError();
    listDriveFilesMock.mockRejectedValueOnce(
      new ChatNetworkError(
        "Drive'a bağlı değilsin ya da Drive iznini vermemişsin.",
      ),
    );
    const user = userEvent.setup();
    render(<DocumentCard />);
    await user.click(screen.getByTestId("tab-drive"));
    expect(await screen.findByTestId("drive-needs-auth")).toBeInTheDocument();
  });
});

describe("DocumentCard Q&A", () => {
  it("posts the question to /document and renders the answer", async () => {
    uploadDocumentMock.mockResolvedValueOnce(fakeDoc);
    askDocumentMock.mockResolvedValueOnce({
      ok: true,
      ui_type: "DocumentAnswer",
      data: {
        doc_id: "doc-1",
        question: "Bu belgede ne var?",
        answer: "Belgede X yazıyor.",
        chunks_used: 1,
        total_chunks: 1,
      },
    });
    const user = userEvent.setup();
    render(<DocumentCard />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    await user.upload(input, new File(["hi"], "x.pdf", { type: "application/pdf" }));
    await screen.findByTestId("document-ready");
    await user.type(screen.getByTestId("qa-input"), "Bu belgede ne var?");
    await user.click(screen.getByTestId("qa-submit"));
    await waitFor(() =>
      expect(askDocumentMock).toHaveBeenCalledWith({
        doc_id: "doc-1",
        question: "Bu belgede ne var?",
      }),
    );
    expect(await screen.findByText("Belgede X yazıyor.")).toBeInTheDocument();
  });

  it("renders friendly error when Q&A returns ok:false", async () => {
    uploadDocumentMock.mockResolvedValueOnce(fakeDoc);
    askDocumentMock.mockResolvedValueOnce({
      ok: false,
      error: { user_message: "Belge cevabı üretilemedi.", retry_after: 15 },
    });
    const user = userEvent.setup();
    render(<DocumentCard />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    await user.upload(input, new File(["hi"], "x.pdf", { type: "application/pdf" }));
    await screen.findByTestId("document-ready");
    await user.type(screen.getByTestId("qa-input"), "test");
    await user.click(screen.getByTestId("qa-submit"));
    expect(await screen.findByTestId("doc-error")).toHaveTextContent(
      /üretilemedi/,
    );
  });

  it("reset returns to picker", async () => {
    uploadDocumentMock.mockResolvedValueOnce(fakeDoc);
    const user = userEvent.setup();
    render(<DocumentCard />);
    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    await user.upload(input, new File(["hi"], "x.pdf", { type: "application/pdf" }));
    await screen.findByTestId("document-ready");
    await user.click(screen.getByTestId("doc-reset"));
    expect(screen.getByTestId("document-card")).toBeInTheDocument();
    expect(screen.queryByTestId("document-ready")).toBeNull();
  });
});
