import { create } from "zustand";

import type { UploadedDocDTO } from "@/api/client";

/** When a user uploads or imports a document, it stays "active" — every
 * subsequent chat / voice question routes to the document Q&A pipeline
 * instead of the general LLM until they explicitly clear it. The store
 * lives outside the modal so closing the DocumentCard doesn't drop the
 * context. */
export interface DocumentContextState {
  activeDoc: UploadedDocDTO | null;
  setActiveDoc: (doc: UploadedDocDTO) => void;
  clearActiveDoc: () => void;
}

export const useDocumentContext = create<DocumentContextState>((set) => ({
  activeDoc: null,
  setActiveDoc: (doc) => set({ activeDoc: doc }),
  clearActiveDoc: () => set({ activeDoc: null }),
}));
