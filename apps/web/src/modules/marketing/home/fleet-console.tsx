"use client";

import {
  AnimatePresence,
  motion,
  useInView,
  useReducedMotion,
} from "motion/react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@akashic-labs/ui";

import { HudLabel } from "~/modules/marketing/ui/hud";

/**
 * Hero visual. Plays the recall loop from the docs (concepts/memory/recall-loop.mdx):
 * a target fails, a lesson is pushed before the retry, the retry passes, the lesson earns flip credit.
 */

const seats = [
  { id: "claude", role: "harness", state: "working" },
  { id: "codex", role: "harness", state: "working" },
  { id: "cursor", role: "harness", state: "idle" },
  { id: "kimi", role: "runner", state: "mail" },
] as const;

interface Beat {
  readonly kind: "agent" | "fail" | "hook" | "lesson" | "ok" | "credit";
  readonly text: string;
}

const beats: readonly Beat[] = [
  { kind: "agent", text: "pytest tests/test_server.py" },
  { kind: "fail", text: "test run hung at start (timeout)" },
  {
    kind: "hook",
    text: 'PreToolUse  aurora recall-at --command "pytest tests/test_server.py"',
  },
  { kind: "lesson", text: "" },
  { kind: "agent", text: "lsof -i :8000  # free the port, then retry" },
  { kind: "ok", text: "pytest tests/test_server.py  ·  12 passed" },
  {
    kind: "credit",
    text: "PostToolUse  flip credit +1  learn:experiment:port-clash",
  },
];

const STEP_MS = 1500;
const HOLD_STEPS = 4;
/** First paint already shows the failure and the hook, so the lesson lands a beat after load. */
const OPENING_STEP = 3;

export const FleetConsole = () => {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);
  const [step, setStep] = useState(reduced ? beats.length : OPENING_STEP);

  useEffect(() => {
    if (reduced || !inView) return;
    const timer = setInterval(() => {
      setStep((value) => (value >= beats.length + HOLD_STEPS ? 1 : value + 1));
    }, STEP_MS);
    return () => clearInterval(timer);
  }, [reduced, inView]);

  const visible = beats.slice(0, Math.min(step, beats.length));
  const credited = step >= beats.length;
  const surfaced = step >= 4;

  return (
    <div
      ref={ref}
      data-testid="fleet-console"
      className="relative overflow-hidden rounded-[22px] border border-white/[0.08] bg-[#050608] shadow-[0_40px_120px_-40px_rgb(10_200_185/0.25)]"
    >
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
        </div>
        <span className="text-mk-faint font-mono text-[11px]">
          aurora · fleet console
        </span>
        <span className="text-mk-faint hidden font-mono text-[11px] sm:block">
          127.0.0.1:8787
        </span>
      </div>

      <div className="grid min-h-[420px] grid-cols-1 md:grid-cols-[190px_1fr] lg:grid-cols-[200px_1fr_260px]">
        <aside className="hidden flex-col gap-1 border-r border-white/[0.06] p-3 md:flex">
          <HudLabel tone="muted" className="mb-2 px-2 text-[9px]">
            Fleet · 4 live seats
          </HudLabel>
          {seats.map((seat) => (
            <div
              key={seat.id}
              className={cn(
                "flex items-center justify-between rounded-lg px-2.5 py-2 text-[13px]",
                seat.id === "codex"
                  ? "bg-white/[0.06] text-white"
                  : "text-white/60",
              )}
            >
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    seat.state === "working" &&
                      "bg-hud-cyan animate-hud-pulse shadow-[0_0_8px_var(--color-hud-cyan)]",
                    seat.state === "idle" && "bg-white/30",
                    seat.state === "mail" && "bg-hud-gold animate-hud-pulse",
                  )}
                />
                {seat.id}
              </span>
              <span className="text-mk-faint font-mono text-[10px]">
                {seat.role}
              </span>
            </div>
          ))}
          <div className="mt-auto flex flex-col gap-1.5 border-t border-white/[0.06] px-2 pt-3 font-mono text-[11px] text-white/45">
            <span>bus · 4 inboxes</span>
            <span>locks · 1 held</span>
            <span>lessons · 812 warm</span>
          </div>
        </aside>

        <div className="flex flex-col gap-2 p-4 font-mono text-[12px] leading-relaxed sm:p-5 sm:text-[12.5px]">
          <div className="text-mk-faint mb-1 flex items-center justify-between text-[11px]">
            <span>seat: codex · task: fix the flaky port test</span>
            <span className="hidden sm:inline">recall-at: armed</span>
          </div>
          <AnimatePresence initial={false}>
            {visible.map((beat, index) => (
              <motion.div
                key={`${beat.kind}-${index}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                <BeatLine beat={beat} />
              </motion.div>
            ))}
          </AnimatePresence>
          {step < beats.length && (
            <span
              className="animate-mk-blink mt-1 inline-block h-4 w-2 bg-white/70"
              aria-hidden
            />
          )}
        </div>

        <aside className="hidden flex-col gap-4 border-l border-white/[0.06] p-4 lg:flex">
          <HudLabel tone="muted" className="text-[9px]">
            Lesson
          </HudLabel>
          <div className="flex flex-col gap-1">
            <span className="text-[14px] font-medium text-white">
              port-clash
            </span>
            <span className="text-mk-faint font-mono text-[10.5px]">
              learn:experiment:port-clash
            </span>
          </div>
          <p className="text-[12.5px] leading-snug text-white/70">
            Use when a test run hangs at start, before you retry: check the port
            first.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Metric label="shown" value={surfaced ? "5" : "4"} />
            <Metric
              label="helped"
              value={credited ? "3" : "2"}
              highlight={credited}
            />
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-mk-faint font-mono text-[10.5px]">
              rank score
            </span>
            <ScoreBar label="relevance" weight={40} value={0.82} />
            <ScoreBar label="importance" weight={20} value={0.6} />
            <ScoreBar label="recency" weight={20} value={0.7} />
            <ScoreBar label="relationship" weight={20} value={0.45} />
          </div>
          <div className="mt-auto flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
            <span className="text-mk-faint font-mono text-[10.5px]">
              usefulness
            </span>
            <span
              className={cn(
                "font-mono text-[12px]",
                credited ? "text-hud-cyan" : "text-white/70",
              )}
            >
              {credited ? "1.20" : "1.10"}
            </span>
          </div>
        </aside>
      </div>
    </div>
  );
};

const BeatLine = ({ beat }: { beat: Beat }) => {
  if (beat.kind === "lesson") {
    return (
      <div className="hud-frame my-1.5 [--hud-cut:10px]">
        <div className="hud-scanlines flex flex-col gap-1.5 px-3.5 py-3">
          <span className="flex items-center gap-2">
            <span className="hud-gem scale-75" />
            <span className="hud-label text-hud-gold hud-glow-gold text-[10px]">
              Lesson surfaced · 1 of 1
            </span>
          </span>
          <span className="text-hud-gold-bright">
            [worked claude helped 2x] Use when a test run hangs at start, before
            you retry: check the port first.
          </span>
          <span className="text-white/55">
            (source: learn:experiment:port-clash)
          </span>
        </div>
      </div>
    );
  }

  const styles: Record<Exclude<Beat["kind"], "lesson">, string> = {
    agent: "text-white",
    fail: "text-hud-red",
    hook: "text-white/45",
    ok: "text-hud-cyan",
    credit: "text-hud-gold",
  };
  const prefix: Record<Exclude<Beat["kind"], "lesson">, string> = {
    agent: "$ ",
    fail: "✕ ",
    hook: "↳ ",
    ok: "✓ ",
    credit: "◆ ",
  };

  return (
    <div className={cn("break-words", styles[beat.kind])}>
      <span className="opacity-70 select-none">{prefix[beat.kind]}</span>
      {beat.text}
    </div>
  );
};

const Metric = ({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) => (
  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
    <span className="text-mk-faint block font-mono text-[10px]">{label}</span>
    <span
      className={cn(
        "font-hud text-xl font-semibold tabular-nums transition-colors duration-500",
        highlight ? "text-hud-cyan hud-glow-cyan" : "text-white",
      )}
    >
      {value}
    </span>
  </div>
);

const ScoreBar = ({
  label,
  weight,
  value,
}: {
  label: string;
  weight: number;
  value: number;
}) => (
  <div className="flex flex-col gap-1">
    <div className="flex justify-between font-mono text-[10px] text-white/45">
      <span>{label}</span>
      <span>{weight}%</span>
    </div>
    <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
      <div
        className="from-hud-cyan-deep to-hud-cyan h-full rounded-full bg-gradient-to-r"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  </div>
);
