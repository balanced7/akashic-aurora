"use client";

import { motion } from "motion/react";
import { useState } from "react";

import { cn } from "@akashic-labs/ui";

import { HudBadge, HudFrame, HudLabel } from "~/modules/marketing/ui/hud";

/**
 * The recall-at-action pipeline from concepts/memory/recall-at-action.mdx and ranker-and-distiller.mdx:
 * rank deterministically, apply the 0.20 floor, skip repeats and self-echo, keep the top three, or show nothing.
 * Scores here are an example run, not measurements.
 */

type Verdict = "shown" | "held" | "below" | "repeat" | "echo";

interface Candidate {
  readonly source: string;
  readonly score: number;
  readonly verdict: Verdict;
}

const scenarios: Record<
  "match" | "silence",
  { label: string; target: string; rows: readonly Candidate[] }
> = {
  match: {
    label: "A strong match",
    target: "pytest tests/test_server.py",
    rows: [
      { source: "port-clash", score: 0.82, verdict: "shown" },
      { source: "pytest-redis-db", score: 0.64, verdict: "shown" },
      { source: "redis-port-drift", score: 0.41, verdict: "shown" },
      { source: "server-start-order", score: 0.33, verdict: "held" },
      { source: "port-clash (shown 2 min ago)", score: 0.8, verdict: "repeat" },
      { source: "my own lesson, this session", score: 0.58, verdict: "echo" },
      { source: "css-token-names", score: 0.09, verdict: "below" },
    ],
  },
  silence: {
    label: "Nothing fits",
    target: "edit docs/brand/palette.md",
    rows: [
      { source: "port-clash", score: 0.14, verdict: "below" },
      { source: "pytest-redis-db", score: 0.11, verdict: "below" },
      { source: "css-token-names", score: 0.18, verdict: "below" },
      { source: "redis-port-drift", score: 0.06, verdict: "below" },
    ],
  },
};

const FLOOR = 0.2;

const verdictLabel: Record<Verdict, string> = {
  shown: "Shown",
  held: "Held back",
  below: "Below floor",
  repeat: "Repeat skipped",
  echo: "Self-echo skipped",
};

const weights = [
  { label: "Relevance", value: 40 },
  { label: "Importance", value: 20 },
  { label: "Recency", value: 20 },
  { label: "Relationship", value: 20 },
];

export const RecallScoreboard = () => {
  const [scenarioKey, setScenarioKey] = useState<"match" | "silence">("match");
  const scenario = scenarios[scenarioKey];
  const shown = scenario.rows.filter((row) => row.verdict === "shown");
  const ordered = [...scenario.rows].sort((a, b) => b.score - a.score);

  return (
    <section
      data-testid="recall-scoreboard"
      className="relative overflow-hidden py-24 sm:py-32"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgb(200_170_110/0.12),transparent_60%)]"
      />
      <div className="mk-container relative">
        <div className="flex flex-col items-center text-center">
          <HudBadge>Recall at action</HudBadge>
          <h2 className="mk-title mt-6 max-w-3xl text-4xl sm:text-5xl lg:text-[3.4rem]">
            Silence beats a{" "}
            <span className="text-hud-gold-bright hud-glow-gold">
              weak hint
            </span>
          </h2>
          <p className="text-mk-muted mt-5 max-w-2xl text-lg">
            Before an edit or command, Aurora ranks every lesson with a formula
            you can read. It drops anything under the floor, skips repeats and
            its own echo, and shows at most three. If nothing fits, it shows
            nothing.
          </p>
        </div>

        <div
          className="mt-12 flex justify-center gap-2"
          role="tablist"
          aria-label="Scenario"
        >
          {(Object.keys(scenarios) as ("match" | "silence")[]).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={scenarioKey === key}
              onClick={() => setScenarioKey(key)}
              className={cn(
                "font-hud h-9 px-4 text-[12px] font-semibold tracking-[0.14em] uppercase transition-colors [clip-path:polygon(8px_0,100%_0,calc(100%-8px)_100%,0_100%)]",
                scenarioKey === key
                  ? "bg-hud-gold text-hud-ink"
                  : "bg-white/[0.06] text-white/60 hover:bg-white/[0.1] hover:text-white",
              )}
            >
              {scenarios[key].label}
            </button>
          ))}
        </div>

        <HudFrame scan className="mx-auto mt-8 max-w-5xl">
          <div className="grid gap-px lg:grid-cols-[1fr_300px]">
            <div className="p-5 sm:p-7">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <span className="font-mono text-[12px] text-white/60">
                  <span className="text-hud-cyan">PreToolUse</span> ·{" "}
                  {scenario.target}
                </span>
                <HudLabel tone="muted" className="text-[10px]">
                  {ordered.length} candidates
                </HudLabel>
              </div>

              <div className="mb-2 grid grid-cols-[96px_1fr_auto] gap-3 sm:grid-cols-[170px_1fr_152px]">
                <span />
                <span className="relative h-3">
                  <span
                    className="hud-label text-hud-gold absolute -translate-x-1/2 text-[9px] whitespace-nowrap"
                    style={{ left: `${FLOOR * 100}%` }}
                  >
                    floor 0.20
                  </span>
                </span>
                <span />
              </div>
              <div className="relative flex flex-col gap-2">
                {ordered.map((row) => (
                  <motion.div
                    layout
                    key={`${scenarioKey}-${row.source}`}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="grid grid-cols-[96px_1fr_auto] items-center gap-3 sm:grid-cols-[170px_1fr_152px]"
                  >
                    <span
                      className={cn(
                        "truncate font-mono text-[12px]",
                        row.verdict === "shown"
                          ? "text-white"
                          : "text-white/45",
                      )}
                    >
                      {row.source}
                    </span>
                    <div className="relative h-2 rounded-sm bg-white/[0.05]">
                      <span
                        aria-hidden
                        className="border-hud-gold/80 absolute -top-1 -bottom-1 z-10 border-l border-dashed"
                        style={{ left: `${FLOOR * 100}%` }}
                      />
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${row.score * 100}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className={cn(
                          "h-full rounded-sm",
                          row.verdict === "shown" &&
                            "from-hud-gold-deep via-hud-gold to-hud-gold-bright bg-gradient-to-r",
                          row.verdict === "held" && "bg-hud-cyan/40",
                          (row.verdict === "repeat" ||
                            row.verdict === "echo") &&
                            "bg-[repeating-linear-gradient(45deg,rgb(255_255_255/0.18)_0_4px,transparent_4px_8px)]",
                          row.verdict === "below" && "bg-white/15",
                        )}
                      />
                    </div>
                    <span
                      className={cn(
                        "font-hud flex items-center justify-end gap-2 text-[10.5px] font-semibold tracking-[0.1em] uppercase",
                        row.verdict === "shown"
                          ? "text-hud-gold"
                          : "text-white/50",
                      )}
                    >
                      <span className="font-mono text-[11px] tracking-normal text-white/50 normal-case tabular-nums">
                        {row.score.toFixed(2)}
                      </span>
                      <span className="hidden sm:inline">
                        {verdictLabel[row.verdict]}
                      </span>
                    </span>
                  </motion.div>
                ))}
              </div>

              <div className="mt-6 rounded-md border border-white/[0.06] bg-black/40 p-4 font-mono text-[12px] leading-relaxed">
                {shown.length > 0 ? (
                  <>
                    <div className="text-hud-gold">
                      Recall-at-action (Akashic) - facts relevant to what
                      you&apos;re about to do:
                    </div>
                    <div className="text-white/80">
                      [worked claude helped 2x] Use when a test run hangs at
                      start, before you retry: check the port first.
                    </div>
                    <div className="text-white/55">
                      ... {shown.length} lessons shown, the rest stay quiet
                    </div>
                  </>
                ) : (
                  <div className="text-white/70">
                    # recall-at-action: nothing relevant (silence beats a weak
                    hint)
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-6 border-white/[0.06] bg-black/30 p-5 max-lg:border-t sm:p-7 lg:border-l">
              <div className="flex flex-col gap-1.5">
                <HudLabel tone="muted" className="text-[10px]">
                  Lessons shown
                </HudLabel>
                <span className="font-hud text-hud-gold-bright hud-glow-gold text-6xl font-semibold tabular-nums">
                  {shown.length}
                  <span className="text-2xl text-white/50"> / 3 max</span>
                </span>
              </div>
              <div className="flex flex-col gap-3">
                <HudLabel tone="muted" className="text-[10px]">
                  Score weights
                </HudLabel>
                {weights.map((weight) => (
                  <div key={weight.label} className="flex flex-col gap-1">
                    <div className="flex justify-between text-[12px]">
                      <span className="text-white/70">{weight.label}</span>
                      <span className="font-hud text-hud-cyan tabular-nums">
                        {weight.value}%
                      </span>
                    </div>
                    <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
                      <div
                        className="bg-hud-cyan h-full"
                        style={{ width: `${weight.value * 2.5}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-mk-faint mt-auto text-[12px] leading-relaxed">
                No language model runs when recall picks lessons. Example
                scores, real rules.
              </p>
            </div>
          </div>
        </HudFrame>
      </div>
    </section>
  );
};
