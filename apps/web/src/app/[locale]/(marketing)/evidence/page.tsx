import { ShieldCheck, TriangleAlert } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import { facts, pillars } from "~/modules/marketing/content/aurora";
import history from "~/modules/marketing/content/generated/aurora-history.json";
import { links, routes } from "~/modules/marketing/content/site";
import { DocQuote } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import {
  HudFrame,
  HudLabel,
  HudStat,
  StatusTag,
} from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "Evidence: what we can show, and what we can't yet",
  description:
    "Every Aurora number names the command that prints it. Here are the counts, the gates, the small results, and the claims we do not make.",
  canonical: routes.evidence,
});

const counts = [
  {
    metric: "Tests",
    value: `${facts.tests} across ${facts.testFiles} files`,
    asOf: facts.readmeAsOf,
    source: "uv run pytest --collect-only -q",
  },
  {
    metric: "Pin-first commits",
    value: "122 RED, 109 GREEN of 771",
    asOf: facts.readmeAsOf,
    source: "README, git log",
  },
  {
    metric: "Review and verification records",
    value: facts.reviewRecords,
    asOf: facts.readmeAsOf,
    source: "docs/library/report/",
  },
  {
    metric: "Task ledger",
    value: `${facts.tasksDone} done of ${facts.tasksRegistered} registered`,
    asOf: facts.readmeAsOf,
    source: "aurora task list",
  },
  {
    metric: "Peer messages over the bridge",
    value: "75 admitted",
    asOf: facts.readmeAsOf,
    source: "README",
  },
  {
    metric: "Commits",
    value: history.totalCommits.toLocaleString("en-US"),
    asOf: history.generatedAt,
    source: "git log --no-merges",
  },
  {
    metric: "Doors",
    value: `${facts.cliVerbs} CLI verbs, ${facts.mcpTools} MCP tools`,
    asOf: "docs",
    source: "concepts/coordination/doors",
  },
];

const gates = [
  "A layer-boundary checker",
  "Door parity between the CLI and MCP",
  "Built-not-wired reachability gates",
  "A doc-currency guard",
  "Acceptance tests committed before the code they gate",
  "A review verdict must cite the preserved record",
];

const notShown = [
  "Whether surfaced lessons improve outcomes at scale. The mechanism is wired and the credit loop runs. The value is not demonstrated.",
  "Concurrency is drill-proven at incident scale, not yet over long durations.",
  "Embeddings pass their gates and are off by default.",
];

const notWired = pillars.flatMap((pillar) =>
  pillar.concepts
    .filter(
      (concept) => concept.status === "partial" || concept.status === "planned",
    )
    .map((concept) => ({ pillar: pillar.name, ...concept })),
);

export default function EvidencePage() {
  return (
    <>
      <PageHero
        backdrop="lattice"
        eyebrow="Evidence"
        title={
          <>
            What we can show.
            <span className="text-mk-muted"> What we can&apos;t yet.</span>
          </>
        }
        description="Agent memory has plenty of benchmark wins that disagree with each other. We publish counts you can rerun, the gates that guard the code, and the claims we refuse to make."
        aside={
          <div className="grid grid-cols-2 gap-8 lg:w-[360px]">
            <HudStat
              value={facts.tests}
              label="Tests"
              note={`as of ${facts.readmeAsOf}`}
            />
            <HudStat
              value={facts.reviewRecords}
              label="Review records"
              note={`as of ${facts.readmeAsOf}`}
              tone="cyan"
            />
          </div>
        }
      >
        <DocQuote
          quote="Every number on this page names the command that prints it. If they disagree, believe the command."
          source="README"
          className="max-w-3xl"
        />
      </PageHero>

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <SectionIntro
            eyebrow="Counts"
            title="Numbers with a date and a command"
          />
          <Reveal className="mt-12">
            <div
              data-testid="evidence-table"
              className="overflow-x-auto rounded-[22px] border border-white/[0.08]"
            >
              <table className="w-full min-w-[680px] text-left text-[14.5px]">
                <thead className="text-mk-faint bg-white/[0.02] text-[12px]">
                  <tr>
                    <th className="px-6 py-3 font-medium">Metric</th>
                    <th className="px-6 py-3 font-medium">Value</th>
                    <th className="px-6 py-3 font-medium">As of</th>
                    <th className="px-6 py-3 font-medium">Prints it</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {counts.map((row) => (
                    <tr key={row.metric}>
                      <td className="px-6 py-4 text-white/85">{row.metric}</td>
                      <td className="font-hud text-hud-gold-bright px-6 py-4 text-[15px] font-semibold tabular-nums">
                        {row.value}
                      </td>
                      <td className="text-mk-faint px-6 py-4 font-mono text-[12.5px]">
                        {row.asOf}
                      </td>
                      <td className="text-mk-muted px-6 py-4 font-mono text-[12.5px]">
                        {row.source}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-10 lg:grid-cols-2">
          <div className="flex flex-col gap-6">
            <SectionIntro
              eyebrow="Gates"
              title="Guards beat good intentions"
              description="CI enforces the method, not just the tests. A pin lands before its fix, and the trail shows it: about three commits in ten are one half of a pin-first pair."
            />
          </div>
          <div className="mk-card flex flex-col gap-3 p-7">
            <HudLabel tone="cyan">What CI checks</HudLabel>
            {gates.map((gate) => (
              <div
                key={gate}
                className="flex gap-3 border-t border-white/[0.06] pt-3 text-[15px] text-white/85 first:border-t-0 first:pt-0"
              >
                <ShieldCheck className="text-hud-cyan mt-0.5 size-4 shrink-0" />
                {gate}
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <Section backdrop="nebula">
        <Container className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-center">
          <SectionIntro
            eyebrow="A real review"
            title="Another fleet found a flaw. We fixed it."
            description="Two independent fleets exchange mail over a signed, outbound-only bridge. A design review by the other fleet found a flaw in our sealed-envelope format. We fixed it, and they adopted the corrected format byte for byte. Inbound mail is parked, never delivered on its own."
          />
          <div className="mk-card grid grid-cols-3 divide-x divide-white/[0.06] overflow-hidden">
            {[
              { value: "75", label: "Messages admitted" },
              { value: "1", label: "Flaw found by a peer" },
              { value: "All", label: "Inbound mail parked first" },
            ].map((item) => (
              <div key={item.label} className="flex flex-col gap-2 p-6">
                <span className="font-hud text-4xl font-semibold text-white tabular-nums">
                  {item.value}
                </span>
                <span className="text-mk-faint text-[13px]">{item.label}</span>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <Section backdrop="network">
        <Container>
          <SectionIntro
            eyebrow="Small results"
            title="Direction, not proof"
            description="Some research results live in the repo with tiny samples. We label them that way."
          />
          <div className="mt-12 grid gap-4 md:grid-cols-2">
            <div className="mk-card flex flex-col gap-3 p-7">
              <span className="font-hud text-hud-gold text-[12px] font-semibold tracking-[0.14em]">
                N = 1
              </span>
              <p className="text-[16px] leading-relaxed text-white/90">
                Decomposing a question beat grounding it on a normative
                question. It flipped a confidently wrong answer to a correct
                one.
              </p>
            </div>
            <div className="mk-card flex flex-col gap-3 p-7">
              <span className="font-hud text-hud-gold text-[12px] font-semibold tracking-[0.14em]">
                N = 1
              </span>
              <p className="text-[16px] leading-relaxed text-white/90">
                Three branches returning different kinds of output found a live
                defect for $0.0155. Five branches returning the same kind found
                nothing for $0.065.
              </p>
            </div>
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-6 lg:grid-cols-2">
          <HudFrame>
            <div className="flex h-full flex-col gap-5 p-8">
              <HudLabel>Not shown</HudLabel>
              <h2 className="mk-title text-3xl">Claims we do not make</h2>
              <ul className="flex flex-col gap-4">
                {notShown.map((item) => (
                  <li
                    key={item}
                    className="flex gap-3 text-[15.5px] leading-relaxed text-white/85"
                  >
                    <TriangleAlert className="text-hud-gold mt-1 size-4 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <p className="text-mk-faint mt-auto text-[13px]">
                From the README, in the project&apos;s own words.
              </p>
            </div>
          </HudFrame>
          <div className="mk-card flex flex-col gap-4 p-8">
            <HudLabel tone="muted">Built, not wired</HudLabel>
            <h2 className="mk-title text-3xl">
              Parts that exist but are not live
            </h2>
            <ul className="flex flex-col divide-y divide-white/[0.06]">
              {notWired.map((item) => (
                <li
                  key={`${item.pillar}-${item.name}`}
                  className="flex items-center justify-between gap-4 py-3"
                >
                  <span className="flex flex-col">
                    <span className="text-[15px] text-white">{item.name}</span>
                    <span className="text-mk-faint text-[12px]">
                      {item.pillar}
                    </span>
                  </span>
                  {item.status && <StatusTag status={item.status} />}
                </li>
              ))}
            </ul>
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <div className="mk-card flex flex-col gap-6 p-8 sm:p-10 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex max-w-2xl flex-col gap-3">
              <HudLabel tone="cyan">Help us measure</HudLabel>
              <h2 className="mk-title text-3xl">
                We want a benchmark for fleets, not chats
              </h2>
              <p className="text-mk-muted text-[16px] leading-relaxed">
                Memory benchmarks test one agent recalling one user. Nobody
                measures handoffs that land, duplicate work avoided, or lessons
                that crossed between harnesses. If you want to help design that,
                open an issue.
              </p>
            </div>
            <ButtonLink href={links.issues} arrow>
              Open an issue
            </ButtonLink>
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
