"use client";

import { Pause, Play, RotateCcw } from "lucide-react";
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
 * Two agents, two days, one memory. The lines mirror real Aurora output captured in a sandbox
 * (learn, recall-feedback) and the recall-at-action example from concepts/memory/recall-at-action.mdx.
 */

interface Line {
  readonly kind: "cmd" | "out" | "fail" | "ok" | "hook" | "lesson" | "dim";
  readonly text: string;
}

interface Frame {
  readonly pane: "a" | "b";
  readonly line: Line;
  readonly record?: "learned" | "credited";
}

const frames: readonly Frame[] = [
  { pane: "a", line: { kind: "cmd", text: "npm run dev" } },
  {
    pane: "a",
    line: { kind: "fail", text: "second start hung: port already in use" },
  },
  {
    pane: "a",
    line: { kind: "dim", text: "# found it: an old server held the port" },
  },
  {
    pane: "a",
    line: {
      kind: "cmd",
      text: 'aurora learn claude --experiment port-clash --tried "started the dev server twice"',
    },
  },
  {
    pane: "a",
    line: {
      kind: "ok",
      text: "[OK] recorded lesson 'port-clash' (category: uncategorized, success: partial)",
    },
    record: "learned",
  },
  { pane: "b", line: { kind: "cmd", text: "pytest tests/test_server.py" } },
  { pane: "b", line: { kind: "fail", text: "test run hung at start" } },
  {
    pane: "b",
    line: {
      kind: "hook",
      text: "PreToolUse → aurora recall-at (before the retry)",
    },
  },
  {
    pane: "b",
    line: {
      kind: "lesson",
      text: "[worked claude helped 2x] Use when a test run hangs at start, before you retry: check the port first.",
    },
  },
  {
    pane: "b",
    line: { kind: "ok", text: "pytest tests/test_server.py  ·  12 passed" },
  },
  {
    pane: "b",
    line: {
      kind: "hook",
      text: "PostToolUse → failed, then passed: flip credit to port-clash",
    },
    record: "credited",
  },
];

const STEP_MS = 1300;

export const LoopReplay = () => {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { margin: "-120px" });
  const [step, setStep] = useState(reduced ? frames.length : 0);
  const [isPlaying, setIsPlaying] = useState(!reduced);

  useEffect(() => {
    if (!isPlaying || !inView) return;
    if (step >= frames.length) {
      setIsPlaying(false);
      return;
    }
    const timer = setTimeout(() => setStep((value) => value + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [isPlaying, inView, step]);

  const shown = frames.slice(0, step);
  const learned = shown.some((frame) => frame.record === "learned");
  const credited = shown.some((frame) => frame.record === "credited");
  const done = step >= frames.length;

  const restart = () => {
    setStep(0);
    setIsPlaying(true);
  };

  return (
    <div
      ref={ref}
      data-testid="loop-replay"
      className="mk-card overflow-hidden p-2 sm:p-3"
    >
      <div className="grid gap-2 lg:grid-cols-[1fr_1fr_280px]">
        <Pane
          title="Claude Code"
          meta="Monday · session 1"
          idle="# Monday. Claude Code opens the repo."
          lines={shown
            .filter((frame) => frame.pane === "a")
            .map((frame) => frame.line)}
          active={!done && frames[step]?.pane === "a"}
        />
        <Pane
          title="Codex"
          meta="Wednesday · session 2"
          idle="# Wednesday. Codex has not started yet."
          lines={shown
            .filter((frame) => frame.pane === "b")
            .map((frame) => frame.line)}
          active={!done && frames[step]?.pane === "b"}
        />
        <div className="flex flex-col gap-3 rounded-xl border border-white/[0.06] bg-[#05080b] p-4">
          <div className="flex items-center justify-between">
            <HudLabel tone="cyan" className="text-[10px]">
              Shared record
            </HudLabel>
            <span className="text-mk-faint font-mono text-[10px]">
              files + redis
            </span>
          </div>
          <RecordRow name="pytest-redis-db" meta="codex · unverified" />
          <RecordRow name="redis-port-drift" meta="claude · helped 1x" />
          <AnimatePresence>
            {learned && (
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn(
                  "rounded-lg border px-3 py-2.5 transition-colors duration-500",
                  credited
                    ? "border-hud-gold/50 bg-hud-gold/[0.07]"
                    : "border-hud-cyan/40 bg-hud-cyan/[0.06]",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[12px] text-white">
                    port-clash
                  </span>
                  <span
                    className={cn(
                      "hud-label rounded-sm px-1.5 py-0.5 text-[9px]",
                      credited
                        ? "bg-hud-gold/20 text-hud-gold"
                        : "bg-hud-cyan/20 text-hud-cyan",
                    )}
                  >
                    {credited ? "helped +1" : "new"}
                  </span>
                </div>
                <span className="text-mk-faint mt-1 block font-mono text-[10.5px]">
                  learn:experiment:port-clash
                </span>
              </motion.div>
            )}
          </AnimatePresence>
          <div className="mt-auto flex items-center gap-2 pt-2">
            <button
              type="button"
              onClick={done ? restart : () => setIsPlaying((value) => !value)}
              className="flex h-8 items-center gap-1.5 rounded-lg bg-white/[0.08] px-3 text-[12px] font-medium text-white transition-colors hover:bg-white/[0.14]"
              aria-label={done ? "Replay" : isPlaying ? "Pause" : "Play"}
            >
              {done ? (
                <RotateCcw className="size-3.5" />
              ) : isPlaying ? (
                <Pause className="size-3.5" />
              ) : (
                <Play className="size-3.5" />
              )}
              {done ? "Replay" : isPlaying ? "Pause" : "Play"}
            </button>
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="from-hud-cyan to-hud-gold h-full bg-gradient-to-r transition-all duration-500"
                style={{ width: `${(step / frames.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const lineStyles: Record<Line["kind"], string> = {
  cmd: "text-white",
  out: "text-white/70",
  fail: "text-hud-red",
  ok: "text-hud-cyan",
  hook: "text-white/45",
  lesson: "",
  dim: "text-white/50",
};

const Pane = ({
  title,
  meta,
  idle,
  lines,
  active,
}: {
  title: string;
  meta: string;
  idle: string;
  lines: Line[];
  active: boolean;
}) => (
  <div
    className={cn(
      "flex min-h-[300px] flex-col rounded-xl border bg-[#07080a] transition-colors duration-500",
      active ? "border-white/15" : "border-white/[0.06]",
    )}
  >
    <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
      <span className="flex items-center gap-2 text-[13px] font-medium text-white">
        <span
          className={cn(
            "size-1.5 rounded-full",
            active ? "bg-hud-cyan animate-hud-pulse" : "bg-white/25",
          )}
        />
        {title}
      </span>
      <span className="text-mk-faint font-mono text-[10.5px]">{meta}</span>
    </div>
    <div className="flex flex-col gap-1.5 p-4 font-mono text-[12px] leading-relaxed">
      {lines.length === 0 && <div className="text-white/45">{idle}</div>}
      {lines.map((line, index) =>
        line.kind === "lesson" ? (
          <motion.div
            key={`${line.kind}-${index}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="hud-frame my-1 [--hud-cut:9px]"
          >
            <div className="flex flex-col gap-1 px-3 py-2.5">
              <span className="hud-label text-hud-gold text-[9.5px]">
                Recall at action
              </span>
              <span className="text-hud-gold-bright">{line.text}</span>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key={`${line.kind}-${index}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn("break-words", lineStyles[line.kind])}
          >
            {line.kind === "cmd" && (
              <span className="text-hud-cyan select-none">$ </span>
            )}
            {line.text}
          </motion.div>
        ),
      )}
      {active && (
        <span
          className="animate-mk-blink mt-0.5 inline-block h-4 w-2 bg-white/70"
          aria-hidden
        />
      )}
    </div>
  </div>
);

const RecordRow = ({ name, meta }: { name: string; meta: string }) => (
  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
    <span className="block font-mono text-[12px] text-white/75">{name}</span>
    <span className="text-mk-faint font-mono text-[10.5px]">{meta}</span>
  </div>
);
