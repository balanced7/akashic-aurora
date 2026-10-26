"use client";

import { AgentAvatar } from "~/components/agent-avatar";
import { Section, Sheet, SheetContent, SheetTrigger } from "~/components/ui/sheet";
import { type Resident, displayName } from "~/lib/bifrost";
import { type Vitals, fleetPulse, useFleet } from "~/lib/fleet";
import { useConsole } from "~/lib/store";
import { cn } from "~/lib/utils";

const PULSE_DOT = {
  green: "bg-ok shadow-[0_0_10px_var(--color-ok)]",
  amber: "bg-amber shadow-[0_0_10px_var(--color-amber)]",
  red: "animate-pulse bg-danger shadow-[0_0_10px_var(--color-danger)]",
} as const;

/** The header's health dot doubles as the door to everything the fleet reports about itself. */
export function FleetPanel() {
  const status = useConsole((s) => s.status);
  const pulse = fleetPulse(status);
  return (
    <Sheet>
      <SheetTrigger
        title={`Fleet: ${pulse.reason}. Open the fleet panel.`}
        className="flex h-8 shrink-0 cursor-pointer items-center gap-2 rounded-lg px-2 text-xs font-semibold text-muted hover:bg-white/5 hover:text-text"
      >
        <span className={cn("size-2.5 rounded-full", PULSE_DOT[pulse.tone])} />
        Fleet
      </SheetTrigger>
      <SheetContent title="Fleet" description={`Health: ${pulse.reason}`}>
        <WorldSection />
        <EngineRoom />
        <FloorSection />
        <ResidentSection />
      </SheetContent>
    </Sheet>
  );
}

const WORLD_DOT: Record<string, string> = {
  live: "bg-ok",
  stale: "bg-amber",
  dead: "bg-danger",
  offline: "bg-faint",
};

function WorldSection() {
  const world = useFleet((s) => s.world);
  const residents = useConsole((s) => s.status?.residents);
  if (!world) return <Section title="World">Reading the roster…</Section>;
  return (
    <Section title="World" hint={world.as_of ? `as of ${new Date(world.as_of).toLocaleTimeString()}` : "no stamp"}>
      {/* The bounds line always shows, whatever it says: blind is a fact, not an empty list. */}
      <p data-testid="world-bounds" className={cn("mb-2 rounded-lg px-2.5 py-1.5 text-xs", world.ok ? "bg-white/[.03] text-muted" : "bg-danger/10 text-danger")}>
        {!world.ok && <b className="mr-1.5 uppercase">blind</b>}
        {world.bounds}
      </p>
      <ul className="space-y-1">
        {world.agents.map((a) => (
          <li key={a.agent} className="flex items-center gap-2 text-[13px]">
            <span className={cn("size-2 rounded-full", WORLD_DOT[(a.state ?? "").toLowerCase()] ?? "bg-faint")} />
            <span className="font-semibold">{displayName(a.agent, residents)}</span>
            <span className="text-faint">
              {a.state ?? "?"}
              {a.phase && a.phase !== "?" ? ` · ${a.phase}` : ""}
              {a.beat_age_s != null ? ` · beat ${Math.max(0, a.beat_age_s).toFixed(1)}s` : ""}
            </span>
            {a.split_brain && <span className="text-danger">split brain</span>}
            {a.churning && (
              <span className="text-amber" title="several incarnations of this seat have come and gone">
                churning
              </span>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}

const HEARTBEAT = { active: "border-ok", idle: "border-amber", offline: "border-faint/50" } as const;

function EngineRoom() {
  const now = useFleet((s) => s.now);
  const residents = useConsole((s) => s.status?.residents);
  if (!now) return null;
  const agents = Object.keys(now.vitals ?? {}).sort();
  const fences = Object.entries(now.fence ?? {}).sort(([a], [b]) => a.localeCompare(b));
  return (
    <Section title="Engine room" hint="heartbeat · runner · lanes · tokens">
      <div className="space-y-1.5">
        {agents.map((id) => (
          <Gauge
            key={id}
            id={id}
            name={displayName(id, residents)}
            v={now.vitals[id] ?? {}}
            seatClass={now.seat_class?.[id]}
            progress={now.progress?.[id]}
          />
        ))}
        {now.dsh_card && <DshCard card={now.dsh_card} name={displayName("dsh_agent", residents)} />}
      </div>
      {fences.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {fences.map(([slug, f]) => (
            <span
              key={slug}
              title={`fence ${slug}: ${f.phase ?? "idle"}`}
              className={cn(
                "rounded-full border px-2 py-0.5 text-[11px]",
                f.phase === "reconciled" ? "border-ok/40 text-ok" : f.phase && f.phase !== "idle" ? "border-amber/40 text-amber" : "border-border text-faint",
              )}
            >
              {slug} · {f.phase ?? "idle"}
            </span>
          ))}
        </div>
      )}
    </Section>
  );
}

function Gauge({
  id,
  name,
  v,
  seatClass,
  progress,
}: {
  id: string;
  name: string;
  v: Vitals;
  seatClass?: string;
  progress?: { phase?: string; elapsed_s?: number };
}) {
  const hb = v.heartbeat ?? "offline";
  const runner = v.runtimes?.runner ?? "";
  const lanes = v.lanes ?? {};
  const tokens = (v.tokens?.prompt ?? 0) + (v.tokens?.completion ?? 0);
  return (
    <div
      className={cn("flex items-center gap-3 rounded-lg border border-border/70 bg-white/[.02] px-2.5 py-1.5", seatClass === "unseated" && "opacity-50")}
      title={`${id}: heartbeat ${hb}, runner ${runner || "n/a"}${seatClass ? `, ${seatClass}` : ""}`}
    >
      <span className={cn("size-3 shrink-0 rounded-full border-2", HEARTBEAT[hb])} />
      <span className="w-24 truncate text-[13px] font-semibold">{name}</span>
      <span
        className={cn(
          "size-2 shrink-0 rounded-full",
          runner === "blocked" || runner === "tripped" ? "bg-danger" : runner === "down" ? "bg-amber" : "bg-ok/70",
        )}
        title={`runner: ${runner || "n/a"}`}
      />
      {/* The trace lane is a capped stream that always reads full, so it lives in the tooltip only. */}
      <span className="text-[11.5px] text-muted tabular-nums" title={`lanes: work ${lanes.work ?? 0}, legacy ${lanes.legacy ?? 0}, trace ${lanes.trace ?? 0}`}>
        <LaneCount n={lanes.work ?? 0} /> work · <LaneCount n={lanes.legacy ?? 0} /> legacy
      </span>
      <span className="text-[11.5px] text-faint tabular-nums" title={v.tokens?.measured === false ? "token use is not measured for this seat" : `${tokens.toLocaleString()} tokens today`}>
        {v.tokens?.measured === false ? "tokens n/a" : `${compact(tokens)} tok`}
      </span>
      <span className="ml-auto flex items-center gap-2 text-[11px] text-faint">
        {progress?.phase && <span title={`${Math.round(progress.elapsed_s ?? 0)}s in this phase`}>{progress.phase}</span>}
        {v.daemon_live && <span className="text-ok">daemon</span>}
        {!!v.pages && <span className="font-bold text-amber">⚡{v.pages}</span>}
      </span>
    </div>
  );
}

function LaneCount({ n }: { n: number }) {
  return <b className={cn("font-semibold", n > 100 ? "text-danger" : n > 10 ? "text-amber" : "text-text")}>{n}</b>;
}

const compact = (n: number) => Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n);

function DshCard({ card, name }: { card: NonNullable<NonNullable<ReturnType<typeof useFleet.getState>["now"]>["dsh_card"]>; name: string }) {
  const tone = card.color === "green" ? "bg-ok" : card.color === "amber" ? "bg-amber" : "bg-faint";
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/70 bg-white/[.02] px-2.5 py-1.5 text-xs">
      <span className={cn("size-2 rounded-full", tone)} />
      <b className="text-[13px]">{name}</b>
      <span className="text-faint">beat {card.beat_age_s == null ? "never" : `${card.beat_age_s}s`}</span>
      {card.phase && card.phase !== "?" && <span className="text-faint">phase {card.phase}</span>}
      {card.profile && <span className="text-faint">profile {card.profile}</span>}
      {card.hop != null && card.hop !== "" && <span className="text-faint">hop {card.hop}</span>}
      {card.plugin_present === false && (
        <span className="text-amber" title="beating on the bus, but its posttool plugin did not stamp presence">
          running without the plugin
        </span>
      )}
    </div>
  );
}

const FLOOR_STATUS: Record<string, string> = {
  fired: "bg-danger",
  clear: "bg-ok",
  unavailable: "bg-amber",
  off: "bg-faint",
};

function FloorSection() {
  const floor = useFleet((s) => s.floor);
  if (!floor) return null;
  return (
    <Section title="Floor" hint={floor.mode ? `mode ${floor.mode}` : undefined}>
      {/* The legend is the adapter's own line, shown verbatim; this surface never adds an "all clear". */}
      {floor.legend && (
        <p className={cn("mb-2 rounded-lg px-2.5 py-1.5 text-xs", floor.ok ? "bg-white/[.03] text-muted" : "bg-danger/10 text-danger")}>
          {floor.legend}
        </p>
      )}
      <ul className="space-y-1">
        {floor.entries.map((e) => (
          <li key={e.key} className="flex items-start gap-2 text-[12.5px]" title={e.detail}>
            <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", FLOOR_STATUS[e.status ?? "clear"] ?? "bg-faint")} />
            <span className="w-24 shrink-0 text-faint">{e.status}</span>
            <span className="min-w-0">
              <span className="font-mono text-[12px]">{e.key}</span>
              {e.detail && <span className="block text-[11.5px] text-faint">{e.detail}</span>}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

type ResidentFull = Resident & { family?: string; team?: string; number?: number | null; formerly?: string[] };

function ResidentSection() {
  const residents = useConsole((s) => s.status?.residents) as Record<string, ResidentFull> | undefined;
  const ids = Object.keys(residents ?? {}).sort((a, b) =>
    (residents?.[a]?.callsign ?? "").localeCompare(residents?.[b]?.callsign ?? ""),
  );
  return (
    <Section title="Residents" hint="the earned names">
      {/* "none read" is not "nobody is a resident": the two must not look the same. */}
      {!ids.length && <p className="text-xs text-danger">No residents read from the registry.</p>}
      <ul className="space-y-1.5">
        {ids.map((id) => {
          const r = residents![id]!;
          const des = [r.family, r.team, r.number != null ? String(r.number) : ""].filter(Boolean).join(" · ");
          const former = r.formerly?.[r.formerly.length - 1];
          return (
            <li key={id} className="flex items-center gap-2.5 text-[13px]" title={id}>
              <AgentAvatar id={id} className="size-6 rounded-lg text-[11px]" />
              <b>{r.callsign}</b>
              {des && <span className="text-faint">{des}</span>}
              {former && <span className="text-faint">formerly {former}</span>}
            </li>
          );
        })}
      </ul>
    </Section>
  );
}
