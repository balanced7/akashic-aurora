"use client";

import { useEffect, useMemo, useState } from "react";

import { AgentAvatar } from "~/components/agent-avatar";
import { buildFeed, chapters, clockTime, displayName, reasoning } from "~/lib/bifrost";
import { elapsed, useFleet } from "~/lib/fleet";
import { useConsole } from "~/lib/store";
import { useNow } from "~/lib/use-now";
import { cn, single } from "~/lib/utils";

/** /api/channels: a room is a bus namespace with at least one live seat in it. */
type Channels = {
  channels: { ns: string; is_default: boolean; count: number; agents: string[] }[];
  default: string;
  not_checked?: string;
};

const CHANNELS_POLL_MS = 10_000;
const STALE_S = 300;

/**
 * The right rail on wide screens: who is doing what and thinking what, the fleet's numbers,
 * chapters to jump through the feed, and the rooms. Every number carries its label.
 */
export function Rail() {
  return (
    <aside className="hidden w-[clamp(250px,24%,340px)] shrink-0 flex-col gap-3 overflow-y-auto py-4 pr-3 xl:flex" aria-label="Fleet rail">
      <NowCards />
      <Throughput />
      {/* rooms above chapters: the chapter list grows long and would push the room switcher below the fold */}
      <Rooms />
      <Chapters />
    </aside>
  );
}

function Card({ title, count, children }: { title: string; count?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-glass-line bg-glass p-3 backdrop-blur-[18px]">
      <h3 className="mb-2 flex items-baseline gap-2 text-[11px] font-semibold tracking-wide text-muted uppercase">
        {title}
        {count && <span className="ml-auto font-normal tracking-normal text-faint normal-case">{count}</span>}
      </h3>
      {children}
    </section>
  );
}

function NowCards() {
  const status = useConsole((s) => s.status);
  const messages = useConsole((s) => s.messages);
  const vitals = useFleet((s) => s.now?.vitals);
  const now = useNow(5000);
  const [open, setOpen] = useState<string | null>(null);
  const known = status?.known ?? [];
  const activities = status?.activities ?? {};
  const live = known.filter((a) => vitals?.[a]?.heartbeat === "active").length;
  // active seats first, then by id
  const order = [...known].sort((x, y) => Number(!!activities[y]?.state) - Number(!!activities[x]?.state) || x.localeCompare(y));

  return (
    <Card title="Now" count={`${live} of ${known.length} beating`}>
      {!status && <p className="text-xs text-faint">Reading the fleet…</p>}
      <ul className="space-y-1">
        {order.map((a) => {
          const seen = status?.agents?.find((r) => r.agent === a)?.last_seen;
          const age = seen ? (now - Date.parse(seen)) / 1000 : Infinity;
          const stale = !(age < STALE_S);
          const act = activities[a];
          const halted = !!status?.halted?.[a];
          const steer = !!status?.signals?.[a]?.steer_pending;
          const active = !!act?.state && act.state !== "idle" && !stale;
          const [chip, tone] = halted
            ? ["halted", "text-danger"]
            : stale
              ? ["offline", "text-faint"]
              : steer
                ? ["steer queued", "text-amber"]
                : active
                  ? ["working", "text-ok"]
                  : ["idle", "text-faint"];
          const why = open === a ? reasoning(messages, a, 8) : [];
          return (
            <li key={a}>
              <button
                type="button"
                onClick={() => setOpen(open === a ? null : a)}
                aria-expanded={open === a}
                title={`${a}: click for its reasoning. ${seen ? `Last beat ${elapsed(seen, now)} ago.` : "Never seen."}`}
                className={cn("flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-1.5 py-1 text-left hover:bg-white/5", stale && "opacity-55")}
              >
                <AgentAvatar id={a} className={cn("size-7 shrink-0 rounded-lg text-[12px]", active && "ring-2 ring-ok/40")} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline gap-2">
                    <b className="truncate text-[13px]">{displayName(a, status?.residents)}</b>
                    <span className={cn("text-[11px]", tone)}>{chip}</span>
                  </span>
                  <span className="block truncate text-[11.5px] text-faint">
                    {act?.state ?? (stale ? "no beat" : "idle")}
                    {act?.detail ? ` · ${act.detail}` : ""}
                  </span>
                </span>
              </button>
              {open === a && (
                <div className="mt-1 mb-2 ml-10 border-l border-border pl-2.5 text-[12px]">
                  <p className="mb-1 text-[11px] text-faint">reasoning, newest first</p>
                  {why.length ? (
                    <ul className="space-y-1 text-muted">
                      {why.map((w, i) => (
                        <li key={i}>
                          <span className="mr-1.5 text-[10.5px] text-faint">{clockTime(w.ts)}</span>
                          {w.text}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    // empty means unrecorded, not unthinking: 💭 lines ride the trace lane only while narration is on
                    <p className="text-faint">No reasoning captured for this seat in this session. Narration may be off.</p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function Throughput() {
  const status = useConsole((s) => s.status);
  const vitals = useFleet((s) => s.now?.vitals);
  const known = status?.known ?? [];
  let live = 0;
  let working = 0;
  let queued = 0;
  let tokens = 0;
  for (const a of known) {
    const v = vitals?.[a];
    if (v?.heartbeat === "active") live++;
    const st = status?.activities?.[a]?.state;
    if (st && st !== "idle") working++;
    queued += v?.lanes?.work ?? 0;
    tokens += (v?.tokens?.prompt ?? 0) + (v?.tokens?.completion ?? 0);
  }
  const tiles: [string, string, string][] = [
    [`${live}/${known.length}`, "seats beating", "Seats whose heartbeat is active"],
    [String(working), "working now", "Seats reporting a non-idle activity"],
    [String(queued), "work queued", "Undrained messages across all work lanes"],
    [Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(tokens), "tokens today", "Prompt plus completion tokens reported by runner seats today"],
  ];
  return (
    <Card title="Throughput">
      <div className="grid grid-cols-2 gap-1.5">
        {tiles.map(([n, label, title]) => (
          <div key={label} title={title} className="rounded-lg bg-white/[.03] px-2.5 py-1.5">
            <div className="text-[17px] font-semibold tabular-nums">{n}</div>
            <div className="text-[11px] text-faint">{label}</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10.5px] text-faint">Counts are of seats, not conversations.</p>
    </Card>
  );
}

function Chapters() {
  const messages = useConsole((s) => s.messages);
  const thread = useConsole((s) => s.thread);
  const residents = useConsole((s) => s.status?.residents);
  const list = useMemo(() => chapters(buildFeed(messages, thread)), [messages, thread]);
  if (list.length < 2) return null;
  return (
    <Card title="Chapters" count={String(list.length)}>
      <ol className="space-y-0.5">
        {list.map((c) => (
          <li key={c.key}>
            <button
              type="button"
              onClick={() => document.querySelector(`[data-feed-key="${CSS.escape(c.key)}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" })}
              className="flex w-full cursor-pointer items-baseline gap-2 rounded-md px-1.5 py-0.5 text-left text-[12px] hover:bg-white/5"
              title={`${c.who}: jump here`}
            >
              <span className="w-12 shrink-0 text-[10.5px] text-faint tabular-nums">{clockTime(c.ts)}</span>
              <span className="min-w-0 truncate">
                <b className="font-semibold">{displayName(c.who, residents)}</b> <span className="text-muted">{c.text}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function Rooms() {
  const room = useConsole((s) => s.room);
  const setRoom = useConsole((s) => s.setRoom);
  const [chans, setChans] = useState<Channels | null>(null);
  useEffect(() => {
    const poll = single(async () => {
      try {
        const r = await fetch("/api/channels", { cache: "no-store" });
        if (r.ok) setChans((await r.json()) as Channels);
      } catch {
        // keep the last reading; rooms change slowly
      }
    });
    void poll();
    const t = setInterval(() => void poll(), CHANNELS_POLL_MS);
    return () => clearInterval(t);
  }, []);
  if (!chans) return null;
  // the room on screen stays listed even after its last seat leaves
  const list = chans.channels.some((c) => c.ns === room) ? chans.channels : [...chans.channels, { ns: room, is_default: false, count: 0, agents: [] }];
  return (
    <Card title="Rooms" count={String(list.length)}>
      <ul className="space-y-0.5">
        {list.map((c) => (
          <li key={c.ns}>
            <button
              type="button"
              onClick={() => setRoom(c.ns)}
              aria-current={c.ns === room}
              title={`namespace ${c.ns} · ${c.count} live seat(s)`}
              className={cn(
                "flex w-full cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-left text-[12.5px] hover:bg-white/5",
                c.ns === room && "bg-accent/10",
              )}
            >
              <b className={cn("font-semibold", c.ns === room && "text-accent")}>{c.ns}</b>
              <span className="text-[10.5px] text-faint">{c.is_default ? "main" : "side"}</span>
              <span className="ml-auto truncate text-[11px] text-faint">{c.agents.join(", ") || "nobody live"}</span>
            </button>
          </li>
        ))}
      </ul>
      {chans.not_checked && <p className="mt-2 text-[10.5px] text-faint">{chans.not_checked}</p>}
    </Card>
  );
}
