import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { routes } from "~/modules/marketing/content/site";
import { HudLabel } from "~/modules/marketing/ui/hud";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

import type { ReactNode } from "react";

/** Framer "full platform" bento: hairline grid, each cell a small live-looking product shot. */
export const PillarBento = () => (
  <Section backdrop="nebula">
    <Container>
      <SectionIntro
        eyebrow="The platform"
        title={
          <>
            Seven layers on one record,
            <br />
            <span className="text-mk-muted">and a contract that holds.</span>
          </>
        }
        description="Start with memory. Add the bus, coordination, doors, trust and the fleet as your work grows. The method is how all of it gets checked."
        action={
          <Link
            href={routes.aurora}
            className="inline-flex items-center gap-1.5 text-[15px] font-medium text-white hover:text-white/70"
          >
            Explore Aurora <ArrowRight className="size-4" />
          </Link>
        }
      />

      <Reveal className="mt-14">
        <div className="grid overflow-hidden rounded-[22px] border border-white/[0.08] md:grid-cols-6">
          <Cell
            href={routes.pillar("knowledge")}
            title="Knowledge"
            className="md:col-span-3"
            label="Layer 03"
          >
            <LessonStack />
          </Cell>
          <Cell
            href={routes.pillar("record")}
            title="The record"
            className="md:col-span-3"
            label="Layer 01"
          >
            <RecordGlyph />
          </Cell>
          <Cell
            href={routes.pillar("bus")}
            title="Bifrost"
            className="md:col-span-2"
            label="Layer 02"
          >
            <MailLines />
          </Cell>
          <Cell
            href={routes.pillar("coordination")}
            title="Coordination"
            className="md:col-span-2"
            label="Layer 04"
          >
            <LockList />
          </Cell>
          <Cell
            href={routes.pillar("doors")}
            title="Doors"
            className="md:col-span-2"
            label="Layer 05"
          >
            <DoorSheet />
          </Cell>
          <Cell
            href={routes.pillar("trust")}
            title="Trust"
            className="md:col-span-2"
            label="Layer 06"
          >
            <TrustRungs />
          </Cell>
          <Cell
            href={routes.pillar("fleet")}
            title="The fleet"
            className="md:col-span-2"
            label="Layer 07"
          >
            <FleetRoster />
          </Cell>
          <Cell
            href={routes.pillar("method")}
            title="The method"
            className="md:col-span-2"
            label="The contract"
          >
            <MethodChips />
          </Cell>
        </div>
      </Reveal>
    </Container>
  </Section>
);

const Cell = ({
  href,
  title,
  label,
  className,
  children,
}: {
  href: string;
  title: string;
  label: string;
  className?: string;
  children: ReactNode;
}) => (
  <Link
    href={href}
    className={cn(
      "group relative flex min-h-[300px] flex-col justify-between gap-6 border-white/[0.08] bg-[#060607] p-6 transition-colors hover:bg-[#0a0a0c] max-md:border-b sm:p-8 md:border-r md:border-b",
      className,
    )}
  >
    <div className="flex flex-1 items-center justify-center">{children}</div>
    <div className="flex items-end justify-between">
      <div className="flex flex-col gap-1">
        <HudLabel tone="muted" className="text-[9.5px]">
          {label}
        </HudLabel>
        <span className="text-[19px] font-medium tracking-tight text-white">
          {title}
        </span>
      </div>
      <ArrowRight className="size-4 text-white/55 transition-all group-hover:translate-x-1 group-hover:text-white" />
    </div>
  </Link>
);

const LessonStack = () => (
  <div className="relative w-full max-w-md overflow-hidden">
    <span
      aria-hidden
      className="via-hud-cyan/[0.07] pointer-events-none absolute inset-x-0 z-10 h-16 animate-[mk-scan-y_4.5s_ease-in-out_infinite] bg-gradient-to-b from-transparent to-transparent"
    />
    {[
      {
        name: "port-clash",
        meta: "claude · helped 2x",
        score: "0.82",
        lit: true,
      },
      {
        name: "pytest-redis-db",
        meta: "codex · unverified",
        score: "0.64",
        lit: true,
      },
      {
        name: "redis-port-drift",
        meta: "claude · helped 1x",
        score: "0.41",
        lit: true,
      },
      {
        name: "lint-before-commit",
        meta: "cursor · benched",
        score: "0.12",
        lit: false,
      },
    ].map((item) => (
      <div
        key={item.name}
        className={cn(
          "mb-2 flex items-center justify-between rounded-xl border px-4 py-3 transition-transform duration-300 group-hover:translate-x-1",
          item.lit
            ? "border-white/[0.08] bg-white/[0.03]"
            : "border-dashed border-white/[0.06] opacity-40",
        )}
      >
        <span className="flex flex-col">
          <span className="font-mono text-[12.5px] text-white">
            {item.name}
          </span>
          <span className="text-mk-faint text-[11px]">{item.meta}</span>
        </span>
        <span
          className={cn(
            "font-hud text-[15px] tabular-nums",
            item.lit ? "text-hud-cyan" : "text-white/55",
          )}
        >
          {item.score}
        </span>
      </div>
    ))}
    <div className="text-mk-faint mt-3 flex items-center gap-2 font-mono text-[10.5px]">
      <span className="bg-hud-gold h-px w-6" /> floor 0.20 · at most three shown
    </div>
  </div>
);

const RecordGlyph = () => (
  <div className="flex w-full max-w-[220px] flex-col gap-2 font-mono text-[11px]">
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-white/80">
      store · what is true now
    </div>
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-white/80">
      ledger · what happened
    </div>
    <div className="flex gap-2">
      <div className="border-hud-cyan/30 text-hud-cyan flex-1 rounded-lg border px-3 py-2">
        files
      </div>
      <div className="flex-1 rounded-lg border border-dashed border-white/[0.12] px-3 py-2 text-white/50">
        redis?
      </div>
    </div>
    <div className="text-mk-faint mt-1 text-[10.5px]">
      corrections supersede · nothing is rewritten
    </div>
  </div>
);

const MailLines = () => (
  <svg viewBox="0 0 220 120" className="w-full max-w-[240px]" aria-hidden>
    {[
      [30, 30],
      [190, 30],
      [30, 95],
      [190, 95],
    ].map(([cx, cy], index) => (
      <g key={index}>
        <circle
          cx={cx}
          cy={cy}
          r="11"
          fill="#0b0c0e"
          stroke="rgb(255 255 255 / 0.15)"
        />
        <circle
          cx={cx}
          cy={cy}
          r="3"
          fill={index === 1 ? "#c8aa6e" : "#0ac8b9"}
        />
      </g>
    ))}
    <circle
      cx="110"
      cy="62"
      r="16"
      fill="#05080b"
      stroke="rgb(10 200 185 / 0.5)"
    />
    <text
      x="110"
      y="66"
      textAnchor="middle"
      fontSize="9"
      fill="#9ff5ec"
      fontFamily="monospace"
    >
      bus
    </text>
    {[
      "M41 30 L95 55",
      "M179 30 L125 55",
      "M41 95 L95 70",
      "M179 95 L125 70",
    ].map((d) => (
      <path
        key={d}
        d={d}
        stroke="rgb(255 255 255 / 0.12)"
        strokeDasharray="3 4"
      />
    ))}
    <circle r="2.5" fill="#c8aa6e">
      <animateMotion
        dur="2.4s"
        repeatCount="indefinite"
        path="M179 30 L125 55 L95 70 L41 95"
      />
    </circle>
  </svg>
);

const LockList = () => (
  <div className="flex w-full max-w-[220px] flex-col gap-2 font-mono text-[11px]">
    {[
      ["T-112", "in_progress", "claude"],
      ["T-113", "claimed", "codex"],
      ["T-114", "proposed", "-"],
    ].map(([id, state, owner]) => (
      <div
        key={id}
        className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2"
      >
        <span className="text-white/80">{id}</span>
        <span className="text-mk-faint">{state}</span>
        <span className="text-hud-cyan">{owner}</span>
      </div>
    ))}
    <div className="text-hud-gold mt-1 flex items-center gap-2">
      <span className="bg-hud-gold animate-hud-pulse size-1.5 rounded-full" />
      lock · router.py · codex · 15m
    </div>
  </div>
);

const DoorSheet = () => (
  <div className="flex w-full max-w-[250px] flex-col gap-2 font-mono text-[11px]">
    {[
      ["aurora <verb>", "121 verbs"],
      ["MCP tools", "76 tools"],
      ["runner ToolBox", "47 guarded"],
    ].map(([door, note]) => (
      <div
        key={door}
        className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2"
      >
        <span className="text-white/80">{door}</span>
        <span className="text-hud-cyan">{note}</span>
      </div>
    ))}
    <div className="text-mk-faint mt-1 flex items-center gap-2 text-[10.5px]">
      <span className="bg-hud-gold h-px w-6" /> parity checked · one memory
    </div>
  </div>
);

const TrustRungs = () => (
  <div className="flex w-full max-w-[220px] flex-col gap-1.5">
    {[
      ["super_admin", "gold"],
      ["admin", "gold"],
      ["member", "cyan"],
      ["restricted", "muted"],
      ["quarantined", "muted"],
    ].map(([role, tone]) => (
      <div
        key={role}
        className={cn(
          "flex items-center justify-between rounded-md border px-3 py-1.5 font-mono text-[10.5px]",
          tone === "gold" &&
            "border-hud-gold/25 bg-hud-gold/[0.05] text-white/85",
          tone === "cyan" &&
            "border-hud-cyan/20 bg-hud-cyan/[0.04] text-white/80",
          tone === "muted" && "border-white/[0.06] text-white/55",
        )}
      >
        <span>{role}</span>
        {role === "quarantined" && (
          <span className="text-hud-gold text-[9px]">default</span>
        )}
      </div>
    ))}
  </div>
);

const FleetRoster = () => (
  <div className="flex w-full max-w-[230px] flex-col gap-1.5 font-mono text-[10.5px]">
    {[
      ["Vandor", "claude"],
      ["Heimdall", "deepseek"],
      ["Navi", "kimi"],
      ["Sunshine Sol", "sol"],
      ["Rill", "dsh_agent"],
      ["Souei", "grok"],
    ].map(([name, id]) => (
      <div key={id} className="flex items-center justify-between">
        <span className="text-white/80">{name}</span>
        <span className="text-mk-faint">{id}</span>
      </div>
    ))}
    <div className="text-hud-gold mt-1 flex items-center gap-2">
      <span className="bg-hud-gold size-1.5 rounded-full" /> you · the Gate
    </div>
  </div>
);

const MethodChips = () => (
  <div className="flex max-w-sm flex-wrap justify-center gap-2">
    {[
      "Red before green",
      "Fenced dual pass",
      "Cite or confess",
      "Drills as acceptance",
      "Proportionality",
      "Guards over discipline",
    ].map((chip) => (
      <span
        key={chip}
        className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[12.5px] text-white/75"
      >
        {chip}
      </span>
    ))}
  </div>
);
