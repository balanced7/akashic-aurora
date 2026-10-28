import { ArrowUpRight } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import {
  doors,
  doorsWhy,
  integrations,
  translationTools,
} from "~/modules/marketing/content/integrations";
import { links, routes } from "~/modules/marketing/content/site";
import { Quickstart } from "~/modules/marketing/home/quickstart";
import { SupportMatrix } from "~/modules/marketing/integrations/support-matrix";
import { TranslationTable } from "~/modules/marketing/integrations/translation-table";
import { LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "Integrations",
  description:
    "One memory, three doors: the shell CLI, MCP tools and the runner ToolBox, plus hooks for Claude, Codex and Cursor. See what each harness supports today.",
  canonical: routes.integrations,
});

export default async function IntegrationsPage(props: {
  searchParams: Promise<{ tool?: string; q?: string; all?: string }>;
}) {
  const searchParams = await props.searchParams;
  const tool =
    translationTools.find((item) => item === searchParams.tool) ??
    "Claude Code";

  return (
    <>
      <PageHero
        eyebrow="Integrations"
        title={
          <>
            One memory.
            <span className="text-mk-muted"> Three doors.</span>
          </>
        }
        description="Aurora meets each harness where it opens up: a shell CLI anywhere, MCP tools where it speaks them, a runner ToolBox for API models, and hooks where they exist."
      >
        <SupportMatrix />
      </PageHero>

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <div className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:items-start">
            <SectionIntro
              eyebrow="Doors"
              title="Three doors, plus hooks"
              description={doorsWhy}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              {doors.map((door, index) => (
                <Reveal key={door.name} delay={index * 0.04} className="h-full">
                  <a
                    href={links.doc(door.doc)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mk-card mk-card-hover group flex h-full flex-col gap-3 p-6"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <HudLabel tone="cyan" className="text-[10px]">
                        {door.kind}
                      </HudLabel>
                      <ArrowUpRight className="text-mk-faint size-4 transition-colors group-hover:text-white" />
                    </div>
                    <span className="text-[18px] font-medium text-white">
                      {door.name}
                    </span>
                    <span className="text-mk-muted text-[14.5px] leading-relaxed">
                      {door.body}
                    </span>
                    <span className="text-mk-faint mt-auto font-mono text-[10.5px]">
                      docs/{door.doc}
                    </span>
                  </a>
                </Reveal>
              ))}
            </div>
          </div>
          <p className="text-mk-faint mt-6 font-mono text-[11px]">
            Door counts as of 2026-10-20. Live checkout and merged branch may
            differ.
          </p>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Harnesses"
            title="One by one"
            description="What each tool supports today. Hooks push recall in; MCP exposes the verbs; a seat puts the agent on the bus."
          />
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {integrations.map((integration, index) => (
              <Reveal
                key={integration.slug}
                delay={index * 0.04}
                className="h-full"
              >
                <LinkCard
                  href={`${routes.integrations}/${integration.slug}`}
                  title={integration.name}
                  description={integration.tagline}
                  className="h-full"
                />
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <SectionIntro
            eyebrow="Setup"
            title="Let your agent install it"
            description="Pick your harness, copy one command, and your agent clones Aurora, adds the aurora command and runs a first session."
          />
          <Reveal>
            <Quickstart />
          </Reveal>
        </Container>
      </Section>

      <Section id="translations">
        <Container>
          <SectionIntro
            eyebrow="Speak their language"
            title="Their term, Aurora's version"
            description="The Aurora docs map every concept to the nearest idea in other agent tools, with links. Pick a tool to see how its terms line up, and where they differ."
          />
          <div className="mt-12">
            <TranslationTable
              tool={tool}
              query={searchParams.q}
              basePath={routes.integrations}
              limit={searchParams.all || searchParams.q ? undefined : 8}
              showAllHref={`${routes.integrations}?tool=${encodeURIComponent(tool)}&all=1#translations`}
            />
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
