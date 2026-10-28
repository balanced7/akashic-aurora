import { getMetadata } from "~/lib/metadata";
import { facts, principles } from "~/modules/marketing/content/aurora";
import history from "~/modules/marketing/content/generated/aurora-history.json";
import { links, routes } from "~/modules/marketing/content/site";
import { AkashicMark, AuroraMark } from "~/modules/marketing/ui/brand";
import { LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel, HudStat } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "About Aurora",
  description:
    "Aurora began as one person's knowledge base, became a team, then a place to work. The origin story of Akashic Aurora, in the project's own voice.",
  canonical: routes.about,
});

const timeline = [
  {
    when: "April 2026",
    title: "The first two days",
    body: "A new window opened, then another. The first asks were plain: keep continuity across sessions, let sessions see each other, and let them work without destroying each other's work. A logger followed, then the first commit.",
  },
  {
    when: "May to June 2026",
    title: "The quiet",
    body: "The project stalled for 43 days. The tooling could not reliably boot itself, and the work stopped. It came back with a different harness, and the impossible stopped feeling impossible.",
  },
  {
    when: "Late June 2026",
    title: "The core in three days",
    body: "An append-only Store and Ledger, a bus with a second model on it, the name Akashic Aurora, recall at action, and the end of per-agent file ownership. Most of the shape still holds.",
  },
  {
    when: "Summer 2026",
    title: "From a memory tool to a fleet",
    body: "More models joined. Trust roles replaced a single shared key. The method became a contract, the Eye made every transcript searchable, and a phone could steer the fleet. The first outside roots arrived.",
  },
  {
    when: "October 2026",
    title: "Two lines, one tree",
    body: "One line had built the house on Windows; another made it portable on Linux. The merge brought 3,627 commits together, with an AI seat reviewing the riskiest files and reporting its own limits.",
  },
] as const;

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title={
          <>
            A home for your agents.
            <span className="text-mk-muted"> Built in the open.</span>
          </>
        }
        description="Aurora began as one person's knowledge base. It became a team, then a place to work. This is the short version, in the project's own voice."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="grid gap-6 lg:grid-cols-2">
          <HudFrame className="h-full">
            <div className="flex h-full flex-col gap-5 p-8 sm:p-10">
              <HudLabel>Origin</HudLabel>
              <p className="text-[19px] leading-relaxed font-medium tracking-tight text-white sm:text-[21px]">
                It started as a knowledge base that remembered everything, so
                that projects were not lost, and so that the knowledge kept
                compounding instead of leaking away between sessions.
              </p>
              <p className="text-mk-muted text-[15.5px] leading-relaxed">
                Then the problem widened. Agents could not see each other, could
                not talk, and could collide in the same files. That turned the
                memory into a team: a bus, a task ledger, short locks and
                handoffs. The goal became a home for your agents that remembers
                your preferences and theirs, and keeps improving the ergonomics
                for both.
              </p>
              <p className="text-mk-faint mt-auto text-[13px]">
                From the project&apos;s history and architecture notes.
              </p>
            </div>
          </HudFrame>
          <div className="mk-card flex flex-col gap-6 p-8 sm:p-10">
            <HudLabel tone="cyan">The names</HudLabel>
            <div className="flex items-start gap-4">
              <AkashicMark className="size-10 shrink-0" />
              <p className="text-[16px] leading-relaxed text-white/85">
                <strong className="font-medium text-white">Akasha</strong> is
                the record nobody rewrites: the Store, the Ledger, the files
                underneath.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <AuroraMark className="size-10 shrink-0" />
              <p className="text-[16px] leading-relaxed text-white/85">
                <strong className="font-medium text-white">Aurora</strong> is
                the order that lights up over it: lessons, stories and the
                wiring that lets agents work together.
              </p>
            </div>
            <p className="text-mk-faint mt-auto text-[13.5px]">
              Bifrost is the bridge, and Heimdall guards it. The Norse names
              came first; the fleet came later. Not related to AWS Aurora.
              Different sky.
            </p>
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <HudStat
            value={history.totalCommits.toLocaleString("en-US")}
            label="Commits"
            note={`since ${history.firstCommit}`}
          />
          <HudStat
            value="6"
            label="Residents"
            note="and one human Gate"
            tone="cyan"
          />
          <HudStat
            value={String(facts.decisions)}
            label="Decisions"
            note="written down, all accepted"
          />
          <HudStat value="1" label="License" note="Apache-2.0" tone="cyan" />
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="The story so far"
            title="One record, then a team, then a place"
            description="The dates are as recorded. Some beats span two days, and a late-evening message can carry the next day's date."
          />
          <ol className="mt-14 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-5">
            {timeline.map((beat, index) => (
              <li key={beat.when} className="bg-[#060607] p-6 sm:p-7">
                <span className="font-hud text-hud-gold/60 text-[11px] font-semibold tracking-[0.16em]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="text-mk-faint mt-4 block font-mono text-[11px]">
                  {beat.when}
                </span>
                <h3 className="mt-2 text-[17px] leading-snug font-medium text-white">
                  {beat.title}
                </h3>
                <p className="text-mk-muted mt-3 text-[13.5px] leading-relaxed">
                  {beat.body}
                </p>
              </li>
            ))}
          </ol>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <SectionIntro
            eyebrow="How we work"
            title="The method ships with the product"
            description="Aurora is built by a fleet of agents and the people who steer them, using Aurora. These are the ideas we hold each other to."
          />
          <ol className="grid gap-3 sm:grid-cols-2">
            {principles.map((principle, index) => (
              <li key={principle} className="mk-card flex gap-4 p-5">
                <span className="font-hud text-hud-gold text-[12px] font-semibold">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="text-[15px] text-white/90">{principle}</span>
              </li>
            ))}
          </ol>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Go deeper"
            title="The rest is in the record"
            description="The vision in one post, the residents with their charters, and the numbers we can actually show."
          />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            <Reveal>
              <LinkCard
                href={routes.blogPost("what-aurora-is-and-why")}
                eyebrow="Blog"
                title="What Aurora is, and why"
                description="The problem, the answer, and the bet on accumulation."
                className="h-full"
              />
            </Reveal>
            <Reveal delay={0.05}>
              <LinkCard
                href={routes.pillar("fleet")}
                eyebrow="The fleet"
                title="Six residents and a Gate"
                description="Callsigns, charters and the gravity-not-walls law."
                className="h-full"
              />
            </Reveal>
            <Reveal delay={0.1}>
              <LinkCard
                href={routes.evidence}
                eyebrow="Evidence"
                title="What we can show"
                description="Counts with commands, and the claims we do not make."
                className="h-full"
              />
            </Reveal>
          </div>
          <p className="text-mk-faint mt-8 text-[13.5px]">
            Every line of Aurora is on{" "}
            <a
              href={links.repo}
              className="text-white underline decoration-white/30 underline-offset-4 hover:decoration-white"
            >
              GitHub
            </a>
            , including the decisions that did not work out.
          </p>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
