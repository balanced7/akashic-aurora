"use client";

import { Play, RotateCw, Rocket, ShieldCheck, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "~/components/ui/sheet";
import { cn, postJson } from "~/lib/utils";

/** One row of /launcher/status: a launchable tag from security/launcher.json and its last run. */
type LauncherRow = {
  tag: string;
  agent_id: string;
  description?: string;
  enabled: boolean;
  status: "running" | "exited" | "never_launched" | string;
  pid: number;
  exit_code: number | null;
  exit_reason: string;
  auto_revive: boolean;
  liveness: { phase: string; detail?: string; turn?: number; stuck_seconds?: number; wedged?: boolean } | null;
};

type Reply = { ok?: boolean; error?: string; pid?: number; supervised?: boolean; unit?: string; action?: string; state_before?: string; note?: string };

const POLL_MS = 5000;
const ARM_MS = 3000;

const EXIT_LABEL: Record<string, string> = {
  running: "running",
  clean: "clean exit",
  exited: "exited",
  killed: "killed",
  error: "error",
  crashed: "crashed",
  token_exhausted: "token exhausted",
  auth_error: "auth error",
  never_launched: "not launched",
};

const EXIT_TONE: Record<string, string> = {
  running: "bg-ok/15 text-ok",
  killed: "bg-amber/15 text-amber",
  token_exhausted: "bg-amber/15 text-amber",
  error: "bg-danger/15 text-danger",
  crashed: "bg-danger/15 text-danger",
  auth_error: "bg-danger/15 text-danger",
};

/** Launch, kill and revive the runner seats in security/launcher.json. Polls only while open. */
export function LauncherPanel() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<LauncherRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  async function refresh() {
    try {
      const r = await fetch("/launcher/status", { cache: "no-store" });
      if (!r.ok) throw new Error(String(r.status));
      setRows((await r.json()) as LauncherRow[]);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }

  // The first read happens on open (an event); the effect only keeps it fresh while open.
  useEffect(() => {
    if (!open) return;
    const t = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(t);
  }, [open]);

  async function act(path: string, body: Record<string, unknown>, ok: (j: Reply) => string, verb: string) {
    try {
      const j = await postJson<Reply>(path, body);
      if (j.ok) toast.success(ok(j));
      else toast.error(j.error ?? `Failed to ${verb} ${String(body.agent_id)}`);
    } catch {
      toast.error(`Could not ${verb}. Is the console backend offline?`);
    }
    void refresh();
  }

  // A supervised seat (AKASHIC_SUPERVISED_SEATS) runs under a systemd unit, so the reply names the
  // unit instead of a pid, and its note says what the unit did not apply (a variant's flags).
  const launch = (tag: string) =>
    act(
      "/launcher/launch",
      { agent_id: tag },
      (j) =>
        j.supervised
          ? `${j.action === "started" ? `Started ${j.unit}` : `${j.unit} already ${j.state_before}`}${j.note ? `: ${j.note}` : ""}`
          : `${tag} started (pid ${j.pid})`,
      "launch",
    );
  const revive = (tag: string) =>
    act(
      "/launcher/revive",
      { agent_id: tag },
      (j) => (j.supervised ? `Restarted ${j.unit}${j.note ? `: ${j.note}` : ""}` : `${tag} revived (pid ${j.pid})`),
      "revive",
    );
  const kill = (tag: string) => act("/launcher/kill", { agent_id: tag }, () => `${tag} terminated`, "kill");
  const arm = (tag: string, on: boolean) =>
    act("/launcher/arm-revive", { agent_id: tag, on }, () => (on ? `Auto-revive armed for ${tag}` : `Auto-revive off for ${tag}`), "toggle auto-revive for");

  const running = rows?.filter((r) => r.status === "running").length ?? 0;
  return (
    <Sheet
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) void refresh();
      }}
    >
      <SheetTrigger asChild>
        <Button variant="ghost" title="Launch and manage agent runners">
          <Rocket />
          Agents
        </Button>
      </SheetTrigger>
      <SheetContent
        title="Agents"
        description={rows ? `${running} of ${rows.length} runners running` : "Reading the launcher…"}
        className="w-[min(620px,96vw)]"
      >
        {failed && <p className="mb-3 rounded-lg bg-danger/10 px-2.5 py-1.5 text-xs text-danger">Launcher status unavailable: cannot say what is running.</p>}
        {rows && !rows.length && (
          <p className="py-3 text-center text-sm text-faint">No runners registered. Add entries to security/launcher.json.</p>
        )}
        <ul className="divide-y divide-white/[.04]">
          {rows?.map((r) => (
            <Row key={r.tag} row={r} onLaunch={launch} onKill={kill} onRevive={revive} onArm={arm} />
          ))}
        </ul>
      </SheetContent>
    </Sheet>
  );
}

function Row({
  row: r,
  onLaunch,
  onKill,
  onRevive,
  onArm,
}: {
  row: LauncherRow;
  onLaunch: (tag: string) => void;
  onKill: (tag: string) => void;
  onRevive: (tag: string) => void;
  onArm: (tag: string, on: boolean) => void;
}) {
  // Kill takes a second click within ARM_MS: it ends a live seat mid-turn.
  const [armedAt, setArmedAt] = useState(0);
  const running = r.status === "running";
  const state = running ? "running" : r.exit_reason || r.status || "never_launched";
  return (
    <li className="py-2.5">
      <div className="flex items-center gap-2">
        <b className="text-[13px]">{r.tag}</b>
        {running && <span className="text-[11px] text-faint">pid {r.pid}</span>}
        <span className={cn("rounded-md px-2 py-0.5 text-[11px] font-semibold", EXIT_TONE[state] ?? "bg-white/5 text-faint")}>
          {EXIT_LABEL[state] ?? state}
          {!running && r.exit_code != null ? ` (code ${r.exit_code})` : ""}
        </span>
        {running && r.liveness && <Liveness l={r.liveness} />}
        {!r.enabled && <span className="text-[11px] text-faint">disabled</span>}
      </div>
      {r.description && <p className="mt-0.5 text-[12px] text-muted">{r.description}</p>}
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        <Button size="sm" variant="primary" disabled={running || !r.enabled} onClick={() => onLaunch(r.tag)}>
          <Play />
          Launch
        </Button>
        <Button size="sm" disabled={!running} onClick={() => onRevive(r.tag)} title="Kill and relaunch: recovers a wedged runner">
          <RotateCw />
          Revive
        </Button>
        <Button
          size="sm"
          variant="warn"
          disabled={!running}
          onClick={(e) => {
            if (armedAt && e.timeStamp - armedAt < ARM_MS) {
              setArmedAt(0);
              onKill(r.tag);
            } else setArmedAt(e.timeStamp);
          }}
          onBlur={() => setArmedAt(0)}
        >
          <Square />
          {armedAt ? "Click again to kill" : "Kill"}
        </Button>
        <Button
          size="sm"
          variant={r.auto_revive ? "primary" : "ghost"}
          aria-pressed={r.auto_revive}
          onClick={() => onArm(r.tag, !r.auto_revive)}
          title="Auto-revive this runner if it wedges (opt-in, off by default)"
        >
          <ShieldCheck />
          Auto-revive
        </Button>
      </div>
    </li>
  );
}

/** A running seat's phase and time in it; a suspected wedge is called out, not averaged away. */
function Liveness({ l }: { l: NonNullable<LauncherRow["liveness"]> }) {
  const s = Math.round(l.stuck_seconds ?? 0);
  const idle = l.phase === "idle" || l.phase === "online";
  return (
    <span
      className={cn("text-[11px]", l.wedged ? "font-semibold text-danger" : idle ? "text-faint" : "text-amber")}
      title={`turn ${l.turn ?? 0} · ${l.phase} for ${s}s${l.wedged ? " · suspected wedge" : ""}`}
    >
      {idle ? "idle" : `${l.phase}${l.detail ? ` · ${l.detail}` : ""} · ${s}s`}
      {l.wedged && " · wedged?"}
    </span>
  );
}
