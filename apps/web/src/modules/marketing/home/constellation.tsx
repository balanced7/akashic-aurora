"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@akashic-labs/ui";

import { AGENTS } from "~/modules/marketing/home/constellation-data";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";

import type { ConstellationEvent } from "~/modules/marketing/home/constellation-data";

const ConstellationScene = dynamic(
  () =>
    import("~/modules/marketing/home/constellation-scene").then(
      (module) => module.ConstellationScene,
    ),
  { ssr: false, loading: () => <ScenePoster /> },
);

interface FeedItem extends ConstellationEvent {
  readonly id: number;
}

const FEED_LENGTH = 5;

/** Section wrapper: copy, the 3D scene, labels that track the seats, and a live event feed. */
export const Constellation = () => {
  const labelRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [totals, setTotals] = useState({ learn: 0, recall: 0 });
  const nextId = useRef(0);
  const stage = useRef<HTMLDivElement>(null);
  const [shouldLoad, setShouldLoad] = useState(false);

  // With reduced motion nothing streams, so show a still snapshot of the feed instead.
  useEffect(() => {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const snapshot: ConstellationEvent[] = [
      { agent: "Codex", kind: "recall" },
      { agent: "Claude Code", kind: "learn" },
      { agent: "Cursor", kind: "recall" },
      { agent: "Kimi", kind: "learn" },
      { agent: "Gemini CLI", kind: "recall" },
    ];
    setFeed(snapshot.map((event, index) => ({ ...event, id: index })));
    setTotals({ learn: 2, recall: 3 });
  }, []);

  // three.js is heavy: fetch it only when the section is about to scroll into view.
  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const onEvent = useCallback((event: ConstellationEvent) => {
    nextId.current += 1;
    const item = { ...event, id: nextId.current };
    setFeed((current) => [item, ...current].slice(0, FEED_LENGTH));
    setTotals((current) => ({
      ...current,
      [event.kind]: current[event.kind] + 1,
    }));
  }, []);

  return (
    <section
      data-testid="constellation"
      className="relative overflow-hidden py-24 sm:py-32"
    >
      <div className="mk-container relative">
        <div className="flex flex-col items-center text-center">
          <span className="text-mk-muted inline-flex items-center gap-2 text-sm font-medium">
            <span className="bg-hud-cyan size-1.5 rounded-full shadow-[0_0_10px_var(--color-hud-cyan)]" />
            One record, every agent
          </span>
          <h2 className="mk-title mt-5 max-w-4xl text-4xl sm:text-6xl lg:text-[4.2rem]">
            Every agent writes to it.
            <br />
            <span className="text-mk-muted">Every agent reads from it.</span>
          </h2>
          <p className="text-mk-muted mt-6 max-w-2xl text-lg leading-relaxed">
            Lessons flow in as agents learn. They flow back out at the moment
            another agent acts. The record in the middle only grows.
          </p>
        </div>

        <div ref={stage} className="relative mt-10 h-[400px] sm:h-[620px]">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgb(10_200_185/0.12),transparent_60%)]"
          />
          {shouldLoad ? (
            <ConstellationScene labelRefs={labelRefs} onEvent={onEvent} />
          ) : (
            <ScenePoster />
          )}
          <div aria-hidden className="pointer-events-none absolute inset-0">
            {AGENTS.map((agent, index) => (
              <span
                key={agent}
                ref={(element) => void (labelRefs.current[index] = element)}
                className="absolute top-0 left-0 rounded-md border border-white/10 bg-black/60 px-2 py-0.5 font-mono text-[11px] whitespace-nowrap text-white/85 opacity-0 backdrop-blur-sm will-change-transform"
              >
                {agent}
              </span>
            ))}
          </div>

          <HudFrame className="absolute bottom-4 left-4 hidden w-[260px] [--hud-cut:12px] sm:block">
            <div
              data-testid="constellation-feed"
              className="flex flex-col gap-2 p-4"
            >
              <div className="flex items-center justify-between">
                <HudLabel className="text-[9.5px]">Live simulation</HudLabel>
                <span className="bg-hud-cyan animate-hud-pulse size-1.5 rounded-full" />
              </div>
              <ul className="flex min-h-[110px] flex-col gap-1 font-mono text-[11px]">
                {feed.map((item, index) => (
                  <li
                    key={item.id}
                    className={cn(
                      "flex justify-between transition-opacity",
                      index > 2 && "opacity-50",
                    )}
                  >
                    <span className="text-white/80">{item.agent}</span>
                    <span
                      className={
                        item.kind === "learn"
                          ? "text-hud-gold"
                          : "text-hud-cyan"
                      }
                    >
                      {item.kind === "learn" ? "learn →" : "← recall"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </HudFrame>

          <div className="absolute right-4 bottom-4 hidden gap-6 sm:flex">
            <Counter label="Lessons learned" value={totals.learn} tone="gold" />
            <Counter
              label="Recalled at action"
              value={totals.recall}
              tone="cyan"
            />
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-6 text-[12.5px]">
          <Legend
            color="bg-hud-gold"
            label="Learn: a seat writes a lesson to the record"
          />
          <Legend
            color="bg-hud-cyan"
            label="Recall at action: the record pushes it to another seat"
          />
          <span className="text-mk-faint">Drag to turn</span>
        </div>
      </div>
    </section>
  );
};

const Counter = ({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "gold" | "cyan";
}) => (
  <div className="flex flex-col items-end">
    <span
      className={cn(
        "font-hud text-3xl font-semibold tabular-nums",
        tone === "gold"
          ? "text-hud-gold-bright hud-glow-gold"
          : "text-hud-cyan hud-glow-cyan",
      )}
    >
      {String(value).padStart(3, "0")}
    </span>
    <HudLabel tone="muted" className="text-[9px]">
      {label}
    </HudLabel>
  </div>
);

const Legend = ({ color, label }: { color: string; label: string }) => (
  <span className="text-mk-muted flex items-center gap-2">
    <span className={cn("size-2 rounded-full", color)} />
    {label}
  </span>
);

const ScenePoster = () => (
  <div className="absolute inset-0 flex items-center justify-center">
    <div className="border-hud-gold/40 size-40 rotate-45 animate-pulse border" />
  </div>
);
