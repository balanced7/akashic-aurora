import { ArrowLeft, ArrowRight, Check, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getMetadata } from "~/lib/metadata";
import { getPillar, pillars } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { NavIconGlyph } from "~/modules/marketing/ui/brand";
import { DocCard, DocQuote } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel, StatusTag } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { PillarCrest } from "~/modules/marketing/ui/pillar-crest";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";
import { Terminal } from "~/modules/marketing/ui/terminal";

/** Every valid slug is known at build time; anything else is a real 404. */
export const dynamicParams = false;

export function generateStaticParams() {
  return pillars.map((pillar) => ({ pillar: pillar.slug }));
}

export async function generateMetadata(props: {
  params: Promise<{ pillar: string; locale: string }>;
}) {
  const params = await props.params;
  const pillar = getPillar(params.pillar);
  if (!pillar) return {};
  return getMetadata({
    title: `${pillar.name}: ${pillar.title}`,
    description: pillar.summary,
    canonical: routes.pillar(pillar.slug),
  })({ params: Promise.resolve({ locale: params.locale }) });
}

export default async function PillarPage(props: {
  params: Promise<{ pillar: string }>;
}) {
  const { pillar: slug } = await props.params;
  const pillar = getPillar(slug);
  if (!pillar) notFound();

  const index = pillars.findIndex((item) => item.slug === pillar.slug);
  const previous = pillars[(index - 1 + pillars.length) % pillars.length];
  const next = pillars[(index + 1) % pillars.length];

  return (
    <>
      <PageHero
        crumbs={[
          { label: "Aurora", href: routes.aurora },
          { label: pillar.name, href: routes.pillar(pillar.slug) },
        ]}
        eyebrow={`${pillar.eyebrow} · ${pillar.name}`}
        title={pillar.title}
        description={pillar.summary}
        aside={
          <PillarCrest
            icon={pillar.icon}
            index={index + 1}
            tone={index % 2 === 0 ? "cyan" : "gold"}
            size={240}
            className="hidden lg:block"
          />
        }
        actions={
          <>
            <ButtonLink
              href={links.doc(pillar.docs[0]?.path ?? "")}
              size="lg"
              arrow
            >
              Read the docs
            </ButtonLink>
            <ButtonLink
              href={links.doc("quickstart")}
              variant="secondary"
              size="lg"
            >
              Quickstart
            </ButtonLink>
          </>
        }
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-center">
          <Terminal
            lines={pillar.terminal}
            title={`aurora · ${pillar.slug}`}
            caret
          />
          <DocQuote quote={pillar.quote} source={pillar.quoteSource} />
        </div>
      </PageHero>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Concepts"
            title="The parts, in one line each"
            description="Each one links to its page in the docs. Parts the docs call built, not wired, or planned are marked."
          />
          <div className="mt-14 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-3">
            {pillar.concepts.map((concept, conceptIndex) => (
              <Reveal
                key={concept.name}
                delay={conceptIndex * 0.03}
                className="h-full"
              >
                <a
                  href={concept.doc ? links.doc(concept.doc) : undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex h-full flex-col gap-3 bg-[#060607] p-6 transition-colors hover:bg-[#0b0b0d]"
                >
                  <span className="flex items-center justify-between gap-3">
                    <span className="text-[17px] font-medium text-white">
                      {concept.name}
                    </span>
                    {concept.status && <StatusTag status={concept.status} />}
                  </span>
                  <span className="text-mk-muted text-[14.5px] leading-relaxed">
                    {concept.body}
                  </span>
                  {concept.doc && (
                    <span className="text-mk-faint mt-auto pt-2 font-mono text-[10.5px] group-hover:text-white/60">
                      docs/{concept.doc}
                    </span>
                  )}
                </a>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-6 lg:grid-cols-2">
          <Reveal className="h-full">
            <div className="mk-card flex h-full flex-col gap-5 p-7 sm:p-9">
              <HudLabel tone="cyan">What you get</HudLabel>
              <ul className="flex flex-col gap-4">
                {pillar.benefits.map((benefit) => (
                  <li
                    key={benefit}
                    className="flex gap-3 text-[17px] text-white"
                  >
                    <Check className="text-hud-cyan mt-1 size-4 shrink-0" />
                    {benefit}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
          <Reveal delay={0.08} className="h-full">
            <HudFrame className="h-full">
              <div className="flex h-full flex-col gap-5 p-7 sm:p-9">
                <HudLabel>Honest limits</HudLabel>
                {pillar.caveats.length > 0 ? (
                  <ul className="flex flex-col gap-4">
                    {pillar.caveats.map((caveat) => (
                      <li
                        key={caveat}
                        className="flex gap-3 text-[15.5px] leading-relaxed text-white/80"
                      >
                        <TriangleAlert className="text-hud-gold mt-1 size-4 shrink-0" />
                        {caveat}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[15.5px] text-white/80">
                    The docs list no open caveats for this part today. If you
                    find one, tell us on GitHub.
                  </p>
                )}
                <p className="text-mk-faint mt-auto text-[13px]">
                  Straight from the docs. We would rather you hear it here.
                </p>
              </div>
            </HudFrame>
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro eyebrow="Go deeper" title="Read the source pages" />
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {pillar.docs.map((doc) => (
              <DocCard key={doc.path} title={doc.title} path={doc.path} />
            ))}
          </div>
        </Container>
      </Section>

      <Section className="py-10 sm:py-12">
        <Container>
          <nav aria-label="Pillars" className="grid gap-4 sm:grid-cols-2">
            {previous && (
              <Link
                href={routes.pillar(previous.slug)}
                className="mk-card mk-card-hover group flex items-center gap-4 p-6"
              >
                <ArrowLeft className="size-4 text-white/55 group-hover:text-white" />
                <span className="flex flex-col">
                  <span className="text-mk-faint text-[12px]">Previous</span>
                  <span className="text-[17px] font-medium text-white">
                    {previous.name}
                  </span>
                </span>
              </Link>
            )}
            {next && (
              <Link
                href={routes.pillar(next.slug)}
                className="mk-card mk-card-hover group flex items-center justify-end gap-4 p-6 text-right"
              >
                <span className="flex flex-col">
                  <span className="text-mk-faint text-[12px]">Next</span>
                  <span className="flex items-center gap-2 text-[17px] font-medium text-white">
                    <NavIconGlyph icon={next.icon} className="text-white/50" />{" "}
                    {next.name}
                  </span>
                </span>
                <ArrowRight className="size-4 text-white/55 group-hover:text-white" />
              </Link>
            )}
          </nav>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
