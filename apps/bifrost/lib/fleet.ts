import { create } from "zustand";

import type { Status } from "./bifrost";

/** /api/now: status + vitals + the extras the engine room reads, in one poll (the TRUTH/NOISE tier). */
export type Vitals = {
  heartbeat?: "active" | "idle" | "offline";
  runtimes?: { runner?: string };
  tokens?: { prompt?: number | null; completion?: number | null; measured?: boolean };
  pages?: number;
  daemon_live?: boolean;
  lanes?: { work?: number; legacy?: number; trace?: number; sig?: number };
};

export type Now = {
  status: Status;
  vitals: Record<string, Vitals>;
  fence?: Record<string, { phase?: string; slug?: string }>;
  seat_class?: Record<string, "runner" | "seat" | "listening" | "unseated" | string>;
  progress?: Record<string, { phase?: string; elapsed_s?: number; pct_estimate?: number | null }>;
  dsh_card?: {
    color?: string;
    beat_age_s?: number | null;
    phase?: string;
    profile?: string;
    hop?: string | number | null;
    plugin_present?: boolean;
  } | null;
};

/** /api/world (spec d622ac): ok=false means BLIND, which is a different fact from "nobody online". */
export type World = {
  ok: boolean;
  as_of?: string | null;
  agents: { agent: string; state?: string; phase?: string; beat_age_s?: number | null; split_brain?: boolean; churning?: boolean }[];
  bounds: string;
};

/** /api/floor (W3/W4): the legend is the adapter's own words; unavailable is never "clear". */
export type Floor = {
  ok: boolean;
  as_of?: string | null;
  mode?: string | null;
  entries: { key: string; status?: "fired" | "clear" | "unavailable" | "off" | string; state?: string; detail?: string }[];
  legend?: string;
};

type FleetState = {
  now: Now | null;
  world: World | null;
  floor: Floor | null;
  set: (patch: Partial<Pick<FleetState, "now" | "world" | "floor">>) => void;
};

export const useFleet = create<FleetState>((set) => ({
  now: null,
  world: null,
  floor: null,
  set: (patch) => set(patch),
}));

export type Pulse = { tone: "green" | "amber" | "red"; reason: string };

/** Fleet health at a glance: red needs attention now, amber is worth a look. */
export function fleetPulse(s: Status | null): Pulse {
  if (!s) return { tone: "amber", reason: "status not read yet" };
  const signals = s.signals ?? {};
  const err = Object.values(signals).some((g) => {
    const x = g as Record<string, unknown>;
    return !!(x.error || x.crashed || x.token_exhausted);
  });
  if (s.paused || err) return { tone: "red", reason: s.paused ? "paused" : "an agent reported an error" };
  const online = new Set((s.agents ?? []).map((a) => a.agent));
  const offline = (s.known ?? []).filter((a) => a !== "user" && !online.has(a));
  const halted = Object.keys(s.halted ?? {}).length;
  const pending = Object.values(signals).some((g) => g.steer_pending || g.nudged);
  const parts = [
    halted ? `${halted} halted` : "",
    offline.length ? `offline: ${offline.join(", ")}` : "",
    pending ? "signals pending" : "",
  ].filter(Boolean);
  return parts.length ? { tone: "amber", reason: parts.join(" · ") } : { tone: "green", reason: "all clear" };
}

export function elapsed(ts: string | undefined, now: number): string {
  if (!ts) return "";
  const s = Math.floor((now - new Date(ts).getTime()) / 1000);
  if (Number.isNaN(s)) return "";
  if (s < 10) return "just now";
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${(s / 60).toFixed(1)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}
