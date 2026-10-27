/** Shared by the 3D scene and its DOM overlay, kept apart so the overlay does not pull in three.js. */
export const AGENTS = [
  "Claude Code",
  "Codex",
  "Cursor",
  "Gemini CLI",
  "OpenCode",
  "Kimi",
] as const;

export interface ConstellationEvent {
  readonly agent: string;
  readonly kind: "learn" | "recall";
}
