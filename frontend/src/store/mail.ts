import { create } from "zustand";

export type MailRangeKind = "daily" | "custom" | "compose";

export interface MailRangeState {
  kind: MailRangeKind;
  customAfter: string; // ISO date "YYYY-MM-DD"
  customBefore: string;
}

export interface MailUIState {
  range: MailRangeState;
  setRangeKind: (kind: MailRangeKind) => void;
  setCustomAfter: (date: string) => void;
  setCustomBefore: (date: string) => void;
  reset: () => void;
}

const today = () => new Date().toISOString().slice(0, 10);
const sevenDaysAgo = () => {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString().slice(0, 10);
};

const initial: MailRangeState = {
  kind: "daily",
  customAfter: sevenDaysAgo(),
  customBefore: today(),
};

export const useMailUI = create<MailUIState>((set) => ({
  range: initial,
  setRangeKind: (kind) =>
    set((s) => ({ range: { ...s.range, kind } })),
  setCustomAfter: (date) =>
    set((s) => ({ range: { ...s.range, customAfter: date } })),
  setCustomBefore: (date) =>
    set((s) => ({ range: { ...s.range, customBefore: date } })),
  reset: () => set({ range: { ...initial, customAfter: sevenDaysAgo(), customBefore: today() } }),
}));

/** Resolve the active range into (after, before) ISO dates the API will use. */
export function resolveRangeBounds(range: MailRangeState): {
  after: string;
  before: string;
} {
  if (range.kind === "custom") {
    return { after: range.customAfter, before: range.customBefore };
  }
  // `daily` is the only summary range left; `compose` short-circuits the
  // fetch path entirely (the card renders a draft instead of a list) but
  // we still return a sensible default so any caller that ignores `kind`
  // doesn't get surprising data.
  const before = today();
  const after = new Date();
  after.setDate(after.getDate() - 1);
  return { after: after.toISOString().slice(0, 10), before };
}
