"use client";

import { displayName, tone } from "~/lib/bifrost";
import { elapsed } from "~/lib/fleet";
import { useConsole } from "~/lib/store";
import { useNow } from "~/lib/use-now";
import { cn } from "~/lib/utils";

const VERB: Record<string, string> = {
  thinking: "thinking",
  reading: "reading",
  searching: "searching",
  inspecting: "inspecting git",
  recalling: "searching memory",
  running: "running a command",
  writing: "writing",
  working: "working",
};
/** Doing-something states sort above idle ones, so the strip leads with what is moving. */
const ORDER: Record<string, number> = { idle: 1 };
const STALE_MS = 5 * 60_000;

const TONE_TEXT = { claude: "text-claude", deepseek: "text-deepseek", user: "text-user", system: "text-system" } as const;

/** Who is doing what right now, just above the composer. Hidden when nobody is active. */
export function ActivityStrip() {
  const activities = useConsole((s) => s.status?.activities);
  const residents = useConsole((s) => s.status?.residents);
  const now = useNow();
  const rows = Object.entries(activities ?? {})
    .filter(([, a]) => a?.state)
    .sort(([x, a], [y, b]) => (ORDER[a.state!] ?? 0) - (ORDER[b.state!] ?? 0) || x.localeCompare(y));
  if (!rows.length) return null;
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 px-5 pt-1.5 pb-1 text-xs" aria-live="polite">
      {rows.map(([id, a]) => {
        const stale = !!a.ts && now - new Date(a.ts).getTime() > STALE_MS;
        return (
          <span key={id} className={cn("flex min-w-0 items-center gap-1.5", stale && "opacity-50")}>
            {a.state !== "idle" && <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-amber" />}
            <b className={TONE_TEXT[tone(id)]}>{displayName(id, residents)}</b>
            <span className="text-muted">{VERB[a.state!] ?? a.state}</span>
            {a.detail && <span className="max-w-72 truncate font-mono text-[11px] text-faint">{a.detail}</span>}
            <span className="text-faint">{elapsed(a.ts, now)}</span>
          </span>
        );
      })}
    </div>
  );
}
