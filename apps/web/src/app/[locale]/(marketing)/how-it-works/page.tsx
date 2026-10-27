import { getMetadata } from "~/lib/metadata";
import { facts } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { Architecture } from "~/modules/marketing/home/architecture";
import { LoopReplay } from "~/modules/marketing/home/loop-replay";
import { LoopTabs } from "~/modules/marketing/home/loop-tabs";
import { RecallScoreboard } from "~/modules/marketing/home/recall-scoreboard";
import { Playground } from "~/modules/marketing/playground/playground";
import { DocCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  InlineCode,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "How Aurora works",
  description:
    "Boot, learn, recall at action, credit, curate and hand off. The loop that gets the right lesson to the next agent at the moment it acts.",
  canonical: routes.howItWorks,
});

/** The recall pipeline in recall-at-action.mdx, step by step. */
const pipeline = [
  {
    step: "Query",
    body: "A PreToolUse hook passes the path or command the agent is about to touch.",
  },
  {
    step: "Scope",
    body: "Lessons are scoped by domain before they compete for a slot.",
  },
  {
    step: "Rank",
    body: "A deterministic score: relevance 40%, importance 20%, recency 20%, relationship 20%.",
  },
  {
    step: "Floor",
    body: "Anything under 0.20 is dropped. A weak hint is worse than none.",
  },
  { step: "Dedupe", body: "Repeats and the agent's own echo are skipped." },
  {
    step: "Usefulness",
    body: "A factor from 0.5 to 1.5, earned from credit, nudges the rank.",
  },
  {
    step: "Top three",
    body: "At most three lessons survive. Each one is fact-checked by rule.",
  },
  {
    step: "Show or stay silent",
    body: "If nothing fits, the agent sees nothing at all.",
  },
];

const curation = [
  {
    rule: "Bench",
    value: "10+ shows, no credit, 10+ days old",
    note: "recall-curate --apply",
  },
  {
    rule: "Trial",
    value: `After ${facts.benchAfterDays} days`,
    note: "a benched lesson gets a trial slot",
  },
  { rule: "Delete", value: "Never", note: "the record only grows" },
  {
    rule: "Graduate",
    value: "When a check enforces it",
    note: "retire it with graduate",
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <PageHero
        eyebrow="How it works"
        title={
          <>
            The loop that gets the right lesson
            <span className="text-mk-muted"> to the next agent</span>
          </>
        }
        description="Boot loads what others knew. Learn gives something back. Recall at action brings it to the moment it applies. Credit counts what helped. Handoff carries your place to the next agent."
        actions={
          <ButtonLink href={links.doc("tutorial")} size="lg" arrow>
            Try it in ten minutes
          </ButtonLink>
        }
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <LoopTabs />
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Across agents"
            title="The lesson does not care which harness wrote it"
            description="One record serves every agent in the fleet. A fix Claude Code found on Monday reaches Codex on Wednesday."
          />
          <Reveal className="mt-14">
            <LoopReplay />
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Inside recall at action"
            title="Eight steps between a hook and a hint"
            description="Every step is a rule you can read in the docs. No step calls a language model."
          />
          <ol className="mt-14 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-4">
            {pipeline.map((item, index) => (
              <li
                key={item.step}
                className="flex flex-col gap-3 bg-[#060607] p-6"
              >
                <span className="font-hud text-hud-gold text-[12px] font-semibold tracking-[0.14em]">
                  STEP {String(index + 1).padStart(2, "0")}
                </span>
                <span className="text-[17px] font-medium text-white">
                  {item.step}
                </span>
                <span className="text-mk-muted text-[14.5px] leading-relaxed">
                  {item.body}
                </span>
              </li>
            ))}
          </ol>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:items-center">
          <SectionIntro
            eyebrow="Try it"
            title="Run the loop in your browser"
            description="Learn a lesson, recall it at a file, credit it, lock a path. A small model of the CLI with real output formats."
          />
          <Reveal>
            <Playground />
          </Reveal>
        </Container>
      </Section>

      <RecallScoreboard />

      <Section>
        <Container className="grid gap-10 lg:grid-cols-2 lg:items-start">
          <div className="flex flex-col gap-6">
            <SectionIntro
              eyebrow="Flip credit"
              title="Credit goes to the lesson that turned a fail into a pass"
              description="A PostToolUse hook reads the result. If that exact target failed earlier and now succeeds, every lesson shown for it earns credit. Agents can also vote with recall-feedback."
            />
            <p className="text-mk-muted text-[15px] leading-relaxed">
              Turn it on with{" "}
              <InlineCode>aurora hooks install --scope user</InlineCode>. The
              installer writes the full hook set, including PostToolUse, which
              flip credit needs.
            </p>
          </div>
          <Reveal>
            <HudFrame tone="cyan">
              <div className="flex flex-col gap-4 p-7 font-mono text-[13px]">
                <HudLabel tone="cyan">Same target, two runs</HudLabel>
                <div className="flex items-center justify-between rounded-md border border-white/[0.06] bg-black/30 px-4 py-3">
                  <span className="text-white/80">
                    pytest tests/test_server.py
                  </span>
                  <span className="text-hud-red">fail</span>
                </div>
                <div className="text-hud-gold px-1 text-[12px]">
                  ↳ lesson shown: port-clash
                </div>
                <div className="flex items-center justify-between rounded-md border border-white/[0.06] bg-black/30 px-4 py-3">
                  <span className="text-white/80">
                    pytest tests/test_server.py
                  </span>
                  <span className="text-hud-cyan">pass</span>
                </div>
                <div className="border-hud-cyan/30 bg-hud-cyan/[0.06] text-hud-cyan rounded-md border px-4 py-3">
                  port-clash: helped +1 · usefulness rises
                </div>
              </div>
            </HudFrame>
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Curation"
            title="Idle lessons step aside. Nothing is deleted."
            description="The curator runs by hand today, not on a schedule. Here are its rules."
          />
          <div className="mt-12 overflow-hidden rounded-[22px] border border-white/[0.08]">
            <table className="w-full text-left text-[15px]">
              <thead className="text-mk-faint bg-white/[0.02] text-[12px]">
                <tr>
                  <th className="px-6 py-3 font-medium">Rule</th>
                  <th className="px-6 py-3 font-medium">When</th>
                  <th className="hidden px-6 py-3 font-medium sm:table-cell">
                    How
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {curation.map((row) => (
                  <tr key={row.rule}>
                    <td className="px-6 py-4 font-medium text-white">
                      {row.rule}
                    </td>
                    <td className="text-mk-muted px-6 py-4">{row.value}</td>
                    <td className="text-mk-faint hidden px-6 py-4 font-mono text-[12.5px] sm:table-cell">
                      {row.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
          <SectionIntro
            eyebrow="Under the loop"
            title="Files first, Redis when it is up"
            description="Every lesson, note and event lands in a local file. Redis adds speed and the live bus. If it goes down, the loop keeps running from the files."
          />
          <Reveal>
            <Architecture />
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro eyebrow="Docs" title="Read the loop at the source" />
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DocCard
              title="Memory and recall"
              path="concepts/memory"
              summary="How the right lesson reaches the next agent."
            />
            <DocCard
              title="Recall at action"
              path="concepts/memory/recall-at-action"
              summary="Lessons pushed right before an edit or command."
            />
            <DocCard
              title="Recall loop"
              path="concepts/memory/recall-loop"
              summary="Counts showings and help, lifts proven lessons."
            />
            <DocCard
              title="Your first session"
              path="tutorial"
              summary="One agent session in a sandbox, about ten minutes."
            />
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
