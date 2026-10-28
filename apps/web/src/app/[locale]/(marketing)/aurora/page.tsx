import { Github } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import { CommandReference } from "~/modules/marketing/aurora/command-reference";
import {
  liveNumbers,
  pillars,
  positioning,
} from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { Architecture } from "~/modules/marketing/home/architecture";
import { Differentiators } from "~/modules/marketing/home/differentiators";
import { FleetConsole } from "~/modules/marketing/home/fleet-console";
import { DocQuote, LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudStat } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { PillarCrest } from "~/modules/marketing/ui/pillar-crest";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "Aurora: a home for your agents",
  description: positioning.subheadline,
  canonical: routes.aurora,
});

export default function AuroraPage() {
  return (
    <>
      <PageHero
        eyebrow="Akashic Aurora"
        title={
          <>
            A home for your agents,
            <span className="text-mk-muted">
              {" "}
              and the wiring that lets a team work.
            </span>
          </>
        }
        description="Aurora keeps what your agents learn, moves mail between them, and grants trust one step at a time. Shared memory, a message bus and a trust layer, on your machine and in the open."
        actions={
          <>
            <ButtonLink href={links.doc("quickstart")} size="lg" arrow>
              Get started
            </ButtonLink>
            <a
              href={links.repo}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.08] px-5 text-[15px] font-medium text-white hover:bg-white/[0.14]"
            >
              <Github className="size-4" /> Source on GitHub
            </a>
          </>
        }
      >
        <FleetConsole />
      </PageHero>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <DocQuote quote={positioning.oneLiner} source="docs/ARCHITECTURE" />
          <div className="grid grid-cols-2 gap-8">
            <HudStat
              value={liveNumbers.lessons}
              label="Lessons"
              note={`in the store, as of ${liveNumbers.asOf}`}
            />
            <HudStat
              value="0"
              label="LLM calls"
              note="when recall picks lessons"
              tone="cyan"
            />
            <HudStat
              value={String(liveNumbers.cliVerbs)}
              label="CLI verbs"
              note={`${liveNumbers.cliVerbsMerged} on the merged branch`}
            />
            <HudStat
              value={String(liveNumbers.mcpTools)}
              label="MCP tools"
              note="parity-checked with the CLI"
              tone="cyan"
            />
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Seven layers and a contract"
            title="Everything rests on one record"
            description="Use memory alone, or turn on the rest as your work grows. Every layer writes to the same append-only record, and the method is how each one is checked."
          />
          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {pillars.map((pillar, index) => (
              <Reveal key={pillar.slug} delay={index * 0.04} className="h-full">
                <LinkCard
                  href={routes.pillar(pillar.slug)}
                  eyebrow={pillar.eyebrow}
                  title={pillar.name}
                  description={pillar.summary}
                  className="h-full"
                >
                  <PillarCrest
                    icon={pillar.icon}
                    index={index + 1}
                    tone={index % 2 === 0 ? "cyan" : "gold"}
                    size={88}
                    className="-ml-2"
                  />
                </LinkCard>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
          <SectionIntro
            eyebrow="Architecture"
            title="Doors on top, files at the bottom"
            description={`Agents reach Aurora through three doors: a CLI with ${liveNumbers.cliVerbs} verbs, an MCP server with ${liveNumbers.mcpTools} tools and a runner ToolBox with ${liveNumbers.runnerTools}. Counts are as of ${liveNumbers.asOf}. Under the layers sits the record, and under the record, plain files.`}
          />
          <Reveal>
            <Architecture />
          </Reveal>
        </Container>
      </Section>

      <Differentiators />

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Reference"
            title="The verbs you will use most"
            description="Most commands take --json, so scripts can parse the output. Run aurora discover to list all of them."
            action={
              <ButtonLink
                href={links.doc("reference/commands")}
                variant="secondary"
                arrow
              >
                Full command reference
              </ButtonLink>
            }
          />
          <div className="mt-14">
            <CommandReference />
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
