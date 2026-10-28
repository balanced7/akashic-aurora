import { cn } from "@akashic-labs/ui";

import { liveNumbers } from "~/modules/marketing/content/aurora";
import { HudLabel } from "~/modules/marketing/ui/hud";

/**
 * The layer stack from the vision deck: doors (CLI, MCP, runner ToolBox) →
 * knowledge, coordination, Bifrost and trust → the record (Store + Ledger) →
 * hybrid storage (files first, Redis when it is up).
 */

const agents = [
  "Claude Code",
  "Codex",
  "Cursor",
  "Gemini CLI",
  "OpenCode",
  "API runners",
];
const layers = [
  { name: "Knowledge", note: "lessons · eye · library" },
  { name: "Coordination", note: "tasks · locks · handoffs" },
  { name: "Bifrost", note: "bus · promoter · console" },
  { name: "Trust", note: "roles · grants · the Gate" },
];

export const Architecture = ({ className }: { className?: string }) => (
  <div
    data-testid="architecture"
    className={cn("mk-card relative overflow-hidden p-5 sm:p-8", className)}
  >
    <div aria-hidden className="mk-grid-bg absolute inset-0 opacity-50" />
    <div className="relative flex flex-col gap-3">
      <Row label="Agents">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {agents.map((agent) => (
            <div
              key={agent}
              className="rounded-lg border border-white/[0.08] bg-[#0b0c0e] px-3 py-2.5 text-center text-[13px] text-white/85"
            >
              {agent}
            </div>
          ))}
        </div>
      </Row>

      <Flow />

      <Row label="Doors">
        <div className="grid grid-cols-3 gap-2">
          <Box title="CLI" note={`${liveNumbers.cliVerbs} verbs · --json`} />
          <Box title="MCP" note={`${liveNumbers.mcpTools} tools`} />
          <Box title="ToolBox" note={`${liveNumbers.runnerTools} guarded`} />
        </div>
      </Row>

      <Flow />

      <Row label="Layers">
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {layers.map((layer) => (
            <Box
              key={layer.name}
              title={layer.name}
              note={layer.note}
              accent={layer.name === "Knowledge"}
            />
          ))}
        </div>
      </Row>

      <Flow label="Bifrost promotes mail that matters" />

      <Row label="Record">
        <div className="hud-frame hud-frame-cyan [--hud-cut:12px]">
          <div className="grid grid-cols-2 gap-px">
            <div className="flex flex-col gap-0.5 px-4 py-3">
              <span className="text-[14px] font-medium text-white">Store</span>
              <span className="text-mk-faint text-[12px]">
                What is true right now
              </span>
            </div>
            <div className="flex flex-col gap-0.5 px-4 py-3">
              <span className="text-[14px] font-medium text-white">Ledger</span>
              <span className="text-mk-faint text-[12px]">
                What happened, in order
              </span>
            </div>
          </div>
        </div>
      </Row>

      <Flow />

      <Row label="Storage">
        <div className="grid grid-cols-[2fr_1fr] gap-2">
          <Box title="Local files" note="every write lands here first" accent />
          <Box title="Redis" note="when it is up · optional" dashed />
        </div>
      </Row>
    </div>
  </div>
);

const Row = ({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) => (
  <div className="grid items-center gap-2 sm:grid-cols-[96px_1fr] sm:gap-4">
    <HudLabel tone="muted" className="text-[9.5px]">
      {label}
    </HudLabel>
    {children}
  </div>
);

const Box = ({
  title,
  note,
  accent,
  dashed,
}: {
  title: string;
  note: string;
  accent?: boolean;
  dashed?: boolean;
}) => (
  <div
    className={cn(
      "flex flex-col gap-0.5 rounded-lg border px-3.5 py-2.5",
      accent
        ? "border-hud-cyan/30 bg-hud-cyan/[0.05]"
        : "border-white/[0.08] bg-[#0b0c0e]",
      dashed && "border-dashed bg-transparent",
    )}
  >
    <span className="text-[14px] font-medium text-white">{title}</span>
    <span className="text-mk-faint font-mono text-[11px]">{note}</span>
  </div>
);

const Flow = ({ label }: { label?: string }) => (
  <div className="grid sm:grid-cols-[96px_1fr] sm:gap-4">
    <span />
    <div className="relative flex h-7 items-center justify-center">
      <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-gradient-to-b from-white/5 via-white/20 to-white/5" />
      <span className="bg-hud-cyan absolute left-1/2 size-1.5 -translate-x-1/2 animate-[mk-flow_1.8s_ease-in-out_infinite] rounded-full shadow-[0_0_8px_var(--color-hud-cyan)]" />
      {label && (
        <span className="text-mk-faint relative ml-32 hidden bg-[#0a0a0b] px-2 font-mono text-[10.5px] sm:block">
          {label}
        </span>
      )}
    </div>
  </div>
);
