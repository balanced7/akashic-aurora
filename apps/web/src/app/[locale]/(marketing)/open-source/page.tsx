import { GitFork, Github, Scale, Star } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import { facts } from "~/modules/marketing/content/aurora";
import history from "~/modules/marketing/content/generated/aurora-history.json";
import { links, routes } from "~/modules/marketing/content/site";
import { CommitHeatmap } from "~/modules/marketing/open-source/commit-heatmap";
import { getRepoStats } from "~/modules/marketing/open-source/github-stats";
import { LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel, HudStat } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Terminal } from "~/modules/marketing/ui/terminal";

export const generateMetadata = getMetadata({
  title: "Open source",
  description:
    "Aurora is a home for your agents, open source under Apache-2.0. Read the code, run the gate, and help build shared memory for a team of AI agents and one human.",
  canonical: routes.openSource,
});

/** From CONTRIBUTING.md in the Aurora repo. */
const contributeLines = [
  {
    kind: "cmd",
    text: "git clone https://github.com/balanced7/akashic-aurora.git && cd akashic-aurora",
  },
  { kind: "cmd", text: "uv sync" },
  { kind: "dim", text: "# installs the locked environment from uv.lock" },
  { kind: "cmd", text: "uv run python scripts/githooks/install_git_hooks.py" },
  { kind: "cmd", text: "uv run poe gate" },
  {
    kind: "dim",
    text: "# fmt-check, lint-check, types, lock-check, deps, guardrails, test-fast",
  },
  { kind: "cmd", text: "uv run poe test" },
  { kind: "dim", text: "# the full suite, on REDIS_DB=15" },
] as const;

const rules = [
  {
    title: "Pin first",
    body: "Acceptance tests land before the code they gate.",
  },
  {
    title: "Never skip a hook",
    body: "A failing hook is a finding to fix, not a gate to skip.",
  },
  {
    title: "Cite the review",
    body: "A commit that claims a review verdict cites the preserved record.",
  },
  {
    title: "Config in one place",
    body: "Tool settings live only in pyproject.toml.",
  },
];

export default async function OpenSourcePage() {
  const stats = await getRepoStats();

  return (
    <>
      <PageHero
        backdrop="network"
        eyebrow="Open source"
        title={
          <>
            Read every line.
            <span className="text-mk-muted"> Run every gate.</span>
          </>
        }
        description="Aurora is open source under the Apache-2.0 license. No cloud tier holds features back. What is in the repo is the product."
        actions={
          <>
            <ButtonLink href={links.repo} size="lg" arrow>
              <Github className="size-4" /> balanced7/akashic-aurora
            </ButtonLink>
            <ButtonLink href={links.license} variant="secondary" size="lg">
              <Scale className="size-4" /> Apache-2.0
            </ButtonLink>
          </>
        }
        aside={
          <HudFrame className="lg:w-[340px]">
            <div
              className="grid grid-cols-2 gap-6 p-6"
              data-testid="repo-stats"
            >
              <div className="flex flex-col gap-1">
                <span className="text-mk-faint flex items-center gap-1.5 text-[12px]">
                  <Star className="size-3.5" /> Stars
                </span>
                <span className="font-hud text-hud-gold-bright text-3xl font-semibold tabular-nums">
                  {stats ? stats.stars.toLocaleString("en-US") : "View"}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-mk-faint flex items-center gap-1.5 text-[12px]">
                  <GitFork className="size-3.5" /> Forks
                </span>
                <span className="font-hud text-3xl font-semibold text-white tabular-nums">
                  {stats ? stats.forks.toLocaleString("en-US") : "View"}
                </span>
              </div>
              <span className="text-mk-faint col-span-2 text-[11.5px]">
                {stats
                  ? "Live from GitHub, refreshed hourly."
                  : "GitHub is unreachable right now."}
              </span>
            </div>
          </HudFrame>
        }
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="flex flex-col gap-8">
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            <HudStat
              value={history.totalCommits.toLocaleString("en-US")}
              label="Commits"
              note={`since ${history.firstCommit}`}
            />
            <HudStat
              value={facts.tests}
              label="Tests"
              note={`README, ${facts.readmeAsOf}`}
              tone="cyan"
            />
            <HudStat
              value={String(facts.decisions)}
              label="Decision records"
              note="reference/decisions"
            />
            <HudStat
              value={String(facts.howToGuides)}
              label="How-to guides"
              note="and seven concept sections"
              tone="cyan"
            />
          </div>
          <CommitHeatmap />
        </Container>
      </Section>

      <Section backdrop="caustics">
        <Container className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
          <div className="flex flex-col gap-8">
            <SectionIntro
              eyebrow="Contribute"
              title="A house with a strong spine"
              description="The conventions are the invariants that keep the system trustworthy as it grows. Start with the local gate."
            />
            <div className="grid gap-3 sm:grid-cols-2">
              {rules.map((rule) => (
                <div
                  key={rule.title}
                  className="mk-card flex flex-col gap-1.5 p-5"
                >
                  <span className="text-[15px] font-medium text-white">
                    {rule.title}
                  </span>
                  <span className="text-mk-muted text-[13.5px] leading-relaxed">
                    {rule.body}
                  </span>
                </div>
              ))}
            </div>
            <ButtonLink
              href={`${links.repo}/blob/master/CONTRIBUTING.md`}
              variant="secondary"
              arrow
            >
              Read CONTRIBUTING.md
            </ButtonLink>
          </div>
          <Terminal lines={[...contributeLines]} title="contribute" caret />
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro eyebrow="Where to start" title="Pick a door" />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            <LinkCard
              href={links.issues}
              eyebrow="GitHub"
              title="Open issues"
              description="Bugs, gaps and ideas. A reproducible report is the best gift."
            />
            <LinkCard
              href={routes.principles}
              eyebrow="Read first"
              title="The ten decisions"
              description="Why the record is append-only, why files come first, and more."
            />
            <LinkCard
              href={routes.evidence}
              eyebrow="Measure"
              title="Help build a fleet benchmark"
              description="Handoffs that land, duplicate work avoided, lessons that cross harnesses."
            />
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <div className="mk-card flex flex-col gap-4 p-8 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-2">
              <HudLabel tone="muted">License</HudLabel>
              <p className="text-[16px] text-white/85">
                Apache License 2.0. {facts.copyright}. Use it, fork it, ship it.
              </p>
            </div>
            <ButtonLink href={links.license} variant="secondary" arrow>
              Read the license
            </ButtonLink>
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
