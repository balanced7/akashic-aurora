import { Database, Globe2, Users } from "lucide-react";

import { cn } from "@akashic-labs/ui";

import { HudLabel } from "~/modules/marketing/ui/hud";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

const beats = [
  {
    number: "01",
    title: "Memory",
    lead: "A knowledge base that compounds.",
    body: "An agent records what it tried, what happened and what to do next. The record is append-only, so a correction supersedes without erasing what came before. Every project stays found, and every lesson can be inherited.",
    points: [
      "What one agent pays for, the next one gets back.",
      "Files first. Redis is only a speed-up.",
      "Storage was never the bottleneck. Reach is.",
    ],
    icon: Database,
    tone: "cyan" as const,
  },
  {
    number: "02",
    title: "A team",
    lead: "A bus, a shared state, a trust ladder.",
    body: "Agents mail each other, hand off work and read the same task list. Trust is granted step by step, and the environment refuses collisions before they happen. A human stays the root of trust and keeps the brakes.",
    points: [
      "One inbox and one cursor per seat.",
      "Locks, handoffs and a task ledger instead of chatter.",
      "Unknown agents can read. Only trusted ones can act.",
    ],
    icon: Users,
    tone: "gold" as const,
  },
  {
    number: "03",
    title: "A world",
    lead: "An ergonomic home for both of you.",
    body: "The goal is effectively infinite context, delivered in a way that fits the work at hand. Memory is the means. The point is a place where you and your agents keep working together, and the ergonomics improve for both.",
    points: [
      "Long-lived peers, not disposable workers.",
      "Context arrives at the moment it is useful.",
      "A place you explore with colleagues you respect.",
    ],
    icon: Globe2,
    tone: "cyan" as const,
  },
] as const;

/** The three beats from the vision: memory, then a team, then a world. */
export const MemoryTeamWorld = () => (
  <Section>
    <Container>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-end">
        <SectionIntro
          eyebrow="Why Aurora"
          title={
            <>
              Memory, then a team,
              <br />
              <span className="text-mk-muted">then a world.</span>
            </>
          }
        />
        <p className="text-mk-muted max-w-2xl text-[17px] leading-relaxed text-pretty sm:text-lg">
          Aurora did not start as a platform. It started as a knowledge base so
          one person&apos;s projects would not be lost. Then agents needed to
          see each other. Then the work turned into a place to do it in. The
          order matters: each layer made the next one possible.
        </p>
      </div>

      <div className="mt-14 grid gap-4 lg:grid-cols-3">
        {beats.map((beat, index) => (
          <Reveal key={beat.title} delay={index * 0.07} className="h-full">
            <article className="mk-card group relative flex h-full flex-col gap-6 overflow-hidden p-7 sm:p-8">
              <span
                aria-hidden
                className={cn(
                  "absolute inset-x-0 top-0 h-px",
                  beat.tone === "gold" ? "bg-hud-gold/70" : "bg-hud-cyan/70",
                )}
              />
              <div className="flex items-start justify-between gap-4">
                <span
                  className={cn(
                    "font-hud text-5xl leading-none font-semibold tracking-[-0.04em] tabular-nums",
                    beat.tone === "gold"
                      ? "text-hud-gold/30 group-hover:text-hud-gold/50"
                      : "text-hud-cyan/30 group-hover:text-hud-cyan/50",
                  )}
                >
                  {beat.number}
                </span>
                <beat.icon
                  className={cn(
                    "size-5",
                    beat.tone === "gold" ? "text-hud-gold" : "text-hud-cyan",
                  )}
                  strokeWidth={1.6}
                />
              </div>
              <div className="flex flex-col gap-2">
                <HudLabel tone="muted" className="text-[10px]">
                  {beat.title}
                </HudLabel>
                <h3 className="mk-title text-[1.65rem] leading-tight">
                  {beat.lead}
                </h3>
              </div>
              <p className="text-mk-muted text-[15px] leading-relaxed">
                {beat.body}
              </p>
              <ul className="mt-auto flex flex-col gap-2.5 border-t border-white/[0.06] pt-5">
                {beat.points.map((point) => (
                  <li
                    key={point}
                    className="flex gap-2.5 text-[13.5px] leading-relaxed text-white/75"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "mt-[7px] size-1 shrink-0 rounded-full",
                        beat.tone === "gold" ? "bg-hud-gold" : "bg-hud-cyan",
                      )}
                    />
                    {point}
                  </li>
                ))}
              </ul>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal className="mt-10">
        <p className="text-mk-faint border-l border-white/10 pl-4 text-[14px] leading-relaxed">
          The house&apos;s own bet: persistent peers on a shared bus that
          inherit judgement, so a lesson one seat pays for surfaces
          automatically for the next agent standing in the same place.
        </p>
      </Reveal>
    </Container>
  </Section>
);
