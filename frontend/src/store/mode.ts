import { create } from "zustand";

export type InteractionMode = "home" | "voice" | "chat";

export interface ModeState {
  mode: InteractionMode;
  setMode: (mode: InteractionMode) => void;
}

export const useMode = create<ModeState>((set) => ({
  mode: "home",
  setMode: (mode) => set({ mode }),
}));

export function deriveModeFromPath(pathname: string): InteractionMode {
  if (pathname.startsWith("/voice")) return "voice";
  if (pathname.startsWith("/chat")) return "chat";
  return "home";
}
