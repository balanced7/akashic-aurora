import { ArrowRight, Check, CircleDashed, Timer } from "lucide-react";
import Link from "next/link";

import { liveNumbers } from "~/modules/marketing/content/aurora";
import { routes } from "~/modules/marketing/content/site";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { Container, Section } from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

const works = [
  "The record: files first, Redis optional, history append-only.",
  "The memory loop: learn, surface, judge, re-rank, bench. No model on the hot path.",
  "The bus: inboxes, handoffs, a promoter and a console with brakes.",
  "The doors: a shell CLI, MCP tools and a runner ToolBox over one memory.",
  "The fleet: named residents, written charters, grants on your word.",
];

const open = [
  `${liveNumbers.knowledgePlanesPushing} knowledge planes can push into a working agent today. Lessons are the one that does; rulings, your own words and research wait to be asked for.`,
  `${liveNumbers.showingsJudged} of ${liveNumbers.showings} lesson showings were ever judged. The rest are unlabelled, not negative.`,
  `${liveNumbers.commandRecallHit} of command queries get a recall hit, against ${liveNumbers.pathRecallHit} of path queries. Commands are most of what agents do, and that is where reach is weakest.`,
  "Whether surfaced lessons improve outcomes at scale is not shown yet. The house says so rather than invent a benchmark.",
];

const done = [
  `${liveNumbers.loopsClosed} value loops are closed. The data plane is sound; the open loops sit in readers, clocks and gates.`,
  "Done means it has demonstrably worked for a while, not that it shipped.",
  "The design is finished when nobody has to point out what relates to what.",
];

const stats = [
  {
    value: liveNumbers.lessons,
    label: "Lessons",
    note: "in the store",
  },
  {
    value: liveNumbers.showingsJudged,
    label: "Showings judged",
    note: `of ${liveNumbers.showings}`,
  },
  {
    value: liveNumbers.loopsClosed,
    label: "Value loops closed",
    note: "of the 10-13 teardown",
  },
] as const;

/** The evidence and trade-offs sections, replaced by one honest block. */
export const HonestStatus = () => (
  <Section>
    <Container>
      <Reveal>
        <HudFrame className="[--hud-cut:22px]">
          <div className="hud-scanlines flex flex-col gap-10 p-7 sm:p-10">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div className="flex max-w-2xl flex-col gap-4">
                <HudLabel>Where it stands</HudLabel>
                <h2 className="mk-title text-3xl sm:text-4xl">
                  What works, what reach still lacks, what done means
                </h2>
                <p className="text-mk-muted text-[15px] leading-relaxed">
                  Aurora underpromises on purpose. These are the numbers from
                  the house&apos;s own checks, including the ones that are not
                  flattering.
                </p>
              </div>
              <div className="flex flex-col gap-1 sm:items-end">
                <span className="hud-label text-hud-gold text-[10px]">
                  As of {liveNumbers.asOf}
                </span>
                <Link
                  href={routes.evidence}
                  className="text-mk-muted inline-flex items-center gap-1.5 text-[14px] hover:text-white"
                >
                  See the evidence <ArrowRight className="size-3.5" />
                </Link>
              </div>
            </div>

            <div className="grid gap-6 border-y border-white/[0.06] py-7 sm:grid-cols-3">
              {stats.map((stat) => (
                <div key={stat.label} className="flex flex-col gap-1.5">
                  <span className="font-hud text-hud-gold-bright text-3xl font-semibold tabular-nums sm:text-4xl">
                    {stat.value}
                  </span>
                  <span className="text-[14px] text-white/85">
                    {stat.label}
                  </span>
                  <span className="text-mk-faint font-mono text-[11px]">
                    {stat.note}
                  </span>
                </div>
              ))}
            </div>

            <div className="grid gap-8 lg:grid-cols-3 lg:gap-10">
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <Check className="text-hud-cyan size-4" strokeWidth={2} />
                  <span className="text-[15px] font-medium text-white">
                    What works
                  </span>
                </div>
                <ul className="flex flex-col gap-3">
                  {works.map((item) => (
                    <li
                      key={item}
                      className="text-mk-muted flex gap-2.5 text-[14px] leading-relaxed"
                    >
                      <span
                        aria-hidden
                        className="bg-hud-cyan mt-[7px] size-1 shrink-0 rounded-full"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <CircleDashed className="text-hud-gold size-4" />
                  <span className="text-[15px] font-medium text-white">
                    What reach still lacks
                  </span>
                </div>
                <ul className="flex flex-col gap-3">
                  {open.map((item) => (
                    <li
                      key={item}
                      className="text-mk-muted flex gap-2.5 text-[14px] leading-relaxed"
                    >
                      <span
                        aria-hidden
                        className="bg-hud-gold mt-[7px] size-1 shrink-0 rounded-full"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <Timer className="text-hud-cyan size-4" />
                  <span className="text-[15px] font-medium text-white">
                    What done means
                  </span>
                </div>
                <ul className="flex flex-col gap-3">
                  {done.map((item) => (
                    <li
                      key={item}
                      className="text-mk-muted flex gap-2.5 text-[14px] leading-relaxed"
                    >
                      <span
                        aria-hidden
                        className="bg-hud-cyan mt-[7px] size-1 shrink-0 rounded-full"
                      />
                      {item}
                    </li>
                  ))}
                </ul>
                <p className="text-mk-faint mt-auto border-l border-white/10 pl-3 text-[13px] leading-relaxed">
                  The house&apos;s tone is to underpromise and overdeliver. The
                  binding problem is reach: right lesson, wrong moment.
                </p>
              </div>
            </div>
          </div>
        </HudFrame>
      </Reveal>
    </Container>
  </Section>
);
