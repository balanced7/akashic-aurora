import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Per-viewer presentation choices, kept in this browser only. */
type Prefs = {
  aurora: boolean;
  auroraSpeed: number;
  auroraIntensity: number;
  /** Trace cards open by default (the operator view) or folded (compact). */
  tracesExpanded: boolean;
  /** The who-is-doing-what strip above the composer. */
  activityStrip: boolean;
  set: (patch: Partial<Omit<Prefs, "set">>) => void;
};

export const usePrefs = create<Prefs>()(
  persist(
    (set) => ({
      aurora: false,
      auroraSpeed: 1,
      auroraIntensity: 0.85,
      tracesExpanded: false,
      activityStrip: true,
      set: (patch) => set(patch),
    }),
    // Rehydrated after mount (Console), so the server render and the first client render agree.
    { name: "bifrost.prefs", skipHydration: true },
  ),
);
