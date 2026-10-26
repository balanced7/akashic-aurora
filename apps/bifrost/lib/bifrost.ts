/** Wire types and pure helpers for the Bifrost bus, as served by scripts/bifrost_ui.py. */

export type BusMessage = {
  id?: string;
  from?: string;
  to?: string;
  kind?: string;
  content?: unknown;
  ts?: string;
  meta?: Record<string, unknown> & {
    hops?: number;
    intent?: string;
    why?: string;
    source?: string;
    verdict?: string;
  };
  epistemic?: {
    currency?: { value?: string };
    claim_kind?: { value?: string };
  };
};

export type Resident = { callsign?: string; vendor?: string };

export type Status = {
  paused: boolean;
  pause?: { paused?: boolean; by?: string; reason?: string; ts?: string };
  agents?: { agent: string; last_seen?: string }[];
  known?: string[];
  activities?: Record<string, { state?: string; detail?: string; ts?: string }>;
  signals?: Record<string, { nudged?: boolean; steer_pending?: number; runner?: boolean }>;
  residents?: Record<string, Resident>;
  halted?: Record<string, { by?: string; reason?: string; ts?: string }>;
  narration?: string;
};

export type Fidelity = "inform" | "steer" | "interrupt";

export const FIDELITY_LABEL: Record<Fidelity, string> = {
  inform: "informed",
  steer: "steered (folds into current task)",
  interrupt: "interrupted (drop & switch)",
};

/** Bookkeeping kinds collapse to a footer counter; they never compete with live work (W70). */
const BOOKKEEPING = new Set([
  "triage-receipt",
  "msg_ack",
  "stale_notice",
  "expectation_dead",
  "packet_integrity_drop",
  "cursor_admin",
]);

export function text(m: BusMessage): string {
  return typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? "");
}

/**
 * Content identity. The dual-write twins (work lane + legacy) share everything but the stream
 * id, so keying on m.id would render every message twice (T044/T045).
 */
export function msgKey(m: BusMessage): string {
  return [m.from ?? "", m.to ?? "", m.kind ?? "", m.ts ?? "", text(m)].join("|");
}

export function isBookkeeping(m: BusMessage): boolean {
  return BOOKKEEPING.has(m.kind ?? "") || text(m).startsWith("[triage-receipt]");
}

/** Seats renamed by the operator before a callsign is ratified. Residents win over this. */
const DISPLAY_OVERRIDES: Record<string, string> = { dsh_agent: "Rill" };
const VENDOR_OVERRIDES: Record<string, string> = { dsh_agent: "deepseek" };

export function displayName(id: string, residents: Record<string, Resident> = {}): string {
  const r = residents[id];
  if (r?.callsign) return r.callsign + (r.vendor ? ` (${r.vendor})` : "");
  const ov = DISPLAY_OVERRIDES[id];
  if (ov !== undefined) {
    const v = VENDOR_OVERRIDES[id];
    return ov + (v ? ` (${v})` : "");
  }
  return id;
}

const VENDOR_HUES: Record<string, [string, string]> = {
  claude: ["#f0a56c", "#e0724f"],
  deepseek: ["#7aa2f7", "#9d7cf7"],
  user: ["#48e6bf", "#2fbf8f"],
};

/** Gradient + letter for an agent chip. Colours key on the vendor; the letter on the callsign. */
export function avatarInfo(
  id: string,
  residents: Record<string, Resident> = {},
): { a: string; b: string; letter: string } {
  const vendor = VENDOR_OVERRIDES[id] ?? id;
  const callsign = residents[id]?.callsign ?? DISPLAY_OVERRIDES[id] ?? "";
  const letter = (callsign[0] ?? id[0] ?? "?").toUpperCase();
  const base = VENDOR_HUES[vendor];
  if (base) return { a: base[0], b: base[1], letter };
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 360;
  return { a: `hsl(${h} 68% 62%)`, b: `hsl(${(h + 38) % 360} 62% 52%)`, letter };
}

/** The colour family a message author renders in. */
export function tone(from: string): "claude" | "deepseek" | "user" | "system" {
  const v = VENDOR_OVERRIDES[from] ?? from;
  return v === "claude" || v === "deepseek" || v === "user" ? v : "system";
}

export function clockTime(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts.replace(" ", "T"));
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Epistemic glyph from typed fields only; a missing axis is UNKNOWN, never default-fresh (T121). */
const CURRENCY_TIER: Record<string, "fresh" | "aging" | "stale" | "unknown"> = {
  current: "fresh",
  aging: "aging",
  stale: "stale",
  superseded: "stale",
  unknown: "unknown",
};
const TIER_GLYPH = { fresh: "●", aging: "◐", stale: "○", unknown: "?" } as const;

export function epistemic(m: BusMessage) {
  const ck = (m.epistemic?.claim_kind?.value ?? "").toLowerCase();
  const marker = ck === "inferred" ? "[infer]" : ck === "guessed" ? "[guess]" : "";
  const cur = (m.epistemic?.currency?.value ?? "unknown").toLowerCase();
  const tier = CURRENCY_TIER[cur] ?? "unknown";
  return { tier, glyph: TIER_GLYPH[tier], marker };
}

/** A 1:1 thread is a client-side view over the shared timeline, not new routing. */
export function inThread(m: BusMessage, peer: string): boolean {
  if (!peer) return true;
  const f = m.from ?? "system";
  const t = m.to ?? "";
  if (f === peer || t === peer) return true;
  if (f === "user" || f === "system") return t === peer || t === "all" || t === "*";
  return false;
}

export type FeedItem =
  | { type: "message"; key: string; m: BusMessage }
  | { type: "system"; key: string; m: BusMessage }
  | { type: "verdict"; key: string; m: BusMessage }
  | { type: "traces"; key: string; agent: string; traces: BusMessage[] };

/**
 * Fold the session buffer into what the log shows. An unbroken stretch of traces becomes one
 * card per agent (T002), even when two agents' tool calls interleave; any real message ends the
 * stretch. Only the system speaks in centred lines; an agent's note is still a message.
 */
export function buildFeed(messages: BusMessage[], peer = ""): FeedItem[] {
  const out: FeedItem[] = [];
  let run = new Map<string, Extract<FeedItem, { type: "traces" }>>();
  for (const m of messages) {
    if (!inThread(m, peer)) continue;
    const key = msgKey(m);
    const kind = m.kind ?? "chat";
    const from = m.from ?? "system";
    if (kind === "trace") {
      const card = run.get(from);
      if (card) card.traces.push(m);
      else {
        const fresh = { type: "traces" as const, key, agent: from, traces: [m] };
        run.set(from, fresh);
        out.push(fresh);
      }
      continue;
    }
    run = new Map();
    if (kind === "verdict" || (kind === "halt" && m.meta?.intent === "verdict")) {
      out.push({ type: "verdict", key, m });
    } else if (from === "system") {
      out.push({ type: "system", key, m });
    } else {
      out.push({ type: "message", key, m });
    }
  }
  return out;
}

export type Chapter = { key: string; who: string; ts?: string; text: string };

/** A chapter starts on a speaker change or after an 8-minute gap (the old rail's rule). */
const CHAPTER_GAP_MS = 8 * 60_000;

/** Feed navigation derived from what was said: nothing is authored, so nothing rots. Newest 14. */
export function chapters(feed: FeedItem[], limit = 14): Chapter[] {
  const out: Chapter[] = [];
  let lastWho = "";
  let lastT = 0;
  for (const item of feed) {
    if (item.type !== "message") continue;
    const who = item.m.from ?? "?";
    const t = item.m.ts ? Date.parse(item.m.ts) : 0;
    if (who !== lastWho || (lastT && t && t - lastT > CHAPTER_GAP_MS)) {
      out.push({ key: item.key, who, ts: item.m.ts, text: text(item.m).replace(/\s+/g, " ").trim().slice(0, 60) });
      lastWho = who;
    }
    if (t) lastT = t;
  }
  return out.slice(-limit);
}

/** An agent's captured reasoning: its 💭 trace lines, newest first. Empty means unrecorded. */
export function reasoning(messages: BusMessage[], agent: string, limit = 6): { text: string; ts?: string }[] {
  const out: { text: string; ts?: string }[] = [];
  for (let i = messages.length - 1; i >= 0 && out.length < limit; i--) {
    const m = messages[i]!;
    if (m.from !== agent || m.kind !== "trace") continue;
    const t = text(m);
    if (t.startsWith("\u{1f4ad}")) out.push({ text: t.replace(/^\u{1f4ad}\s*/u, ""), ts: m.ts });
  }
  return out;
}
