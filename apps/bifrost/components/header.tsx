"use client";

import { Pause, Play } from "lucide-react";
import { toast } from "sonner";

import { EpisodeChip } from "~/components/episode";
import { FleetPanel } from "~/components/fleet-panel";
import { LauncherPanel } from "~/components/launcher-panel";
import { SettingsPanel } from "~/components/settings-panel";
import { Button } from "~/components/ui/button";
import { type Status, displayName } from "~/lib/bifrost";
import { useConsole } from "~/lib/store";
import { cn, postJson } from "~/lib/utils";

export function Header() {
  const status = useConsole((s) => s.status);
  const connected = useConsole((s) => s.connected);
  const paused = !!status?.paused;

  async function togglePause() {
    try {
      useConsole.getState().setStatus(await postJson<Status>(paused ? "/resume" : "/pause"));
    } catch {
      toast.error("Control failed. Is the bus offline?");
    }
  }

  return (
    <header className="sticky top-3 z-10 mx-3 flex h-[62px] shrink-0 items-center gap-3.5 rounded-lg border border-glass-line bg-glass px-5 shadow-[inset_0_1px_0_rgba(255,255,255,.06)] backdrop-blur-[26px] backdrop-saturate-[1.35]">
      <div className="flex shrink-0 items-center gap-2.5 font-[650] tracking-[.2px]">
        <div className="size-[26px] rounded-lg bg-[conic-gradient(from_210deg,#7aa2f7,#9d7cf7,#e0915c,#7aa2f7)] shadow-[0_0_18px_rgba(122,162,247,.45)]" />
        Bifrost
        <small className="hidden font-[450] text-muted sm:inline">live agent console</small>
      </div>
      <span
        role="status"
        title={connected ? "live stream connected" : "stream disconnected, reconnecting"}
        className={cn(
          "size-2 shrink-0 rounded-full",
          connected ? "bg-ok shadow-[0_0_8px_var(--color-ok)]" : "animate-pulse bg-danger",
        )}
      >
        <span className="sr-only">{connected ? "connected" : "reconnecting"}</span>
      </span>
      <FleetPanel />
      <AgentPills status={status} />
      <LauncherPanel />
      <EpisodeChip />
      <SettingsPanel />
      <Button variant={paused ? "warn" : "default"} onClick={togglePause} disabled={!status}>
        {paused ? <Play /> : <Pause />}
        {paused ? "Resume" : "Pause"}
      </Button>
    </header>
  );
}

function AgentPills({ status }: { status: Status | null }) {
  const recipients = useConsole((s) => s.recipients);
  const toggleRecipient = useConsole((s) => s.toggleRecipient);
  if (!status) return <div className="flex-1" />;

  const online = new Set((status.agents ?? []).map((a) => a.agent));
  const known = new Set(status.known ?? []);
  const roster = [...new Set([...(status.known ?? []), ...online, "user"])];

  return (
    <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 overflow-x-auto py-1">
      {roster.map((id) => {
        const isOnline = online.has(id) || id === "user";
        const sig = status.signals?.[id] ?? {};
        const halted = status.halted?.[id];
        const activity = status.activities?.[id];
        const selected = recipients.includes(id);
        const unregistered = !known.has(id) && id !== "user";
        return (
          <button
            key={id}
            type="button"
            disabled={id === "user"}
            onClick={(e) => toggleRecipient(id, e.shiftKey || e.ctrlKey || e.metaKey)}
            title={
              id === "user"
                ? "you"
                : `Message ${displayName(id, status.residents)}. Shift- or Ctrl-click adds to a multi-select.` +
                  (activity?.detail ? `\nNow: ${activity.state ?? ""} ${activity.detail}` : "")
            }
            className={cn(
              "flex h-7 shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-xs font-semibold transition",
              "border-border bg-panel/70 enabled:cursor-pointer enabled:hover:border-[#39405a]",
              !isOnline && "text-faint",
              selected && "border-accent/50 bg-accent/10",
            )}
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                isOnline ? "bg-ok" : "bg-faint/60",
                activity?.state === "running" && "animate-pulse bg-amber",
              )}
            />
            {displayName(id, status.residents)}
            {!!sig.steer_pending && (
              <span className="text-accent" title="steer facts queued">
                ↝{sig.steer_pending}
              </span>
            )}
            {sig.nudged && (
              <span className="text-amber" title="interrupt pending">
                ⚡
              </span>
            )}
            {halted && (
              <span className="text-danger" title={halted.reason ?? "no reason given"}>
                halted
              </span>
            )}
            {unregistered && (
              <span className="text-amber" title="online but not ACL-registered">
                unregistered
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
