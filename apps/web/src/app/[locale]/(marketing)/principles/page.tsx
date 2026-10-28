import { ArrowUpRight } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import {
  decisions,
  laws,
  principles,
} from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudBadge, HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "Principles",
  description:
    "The nine working ideas, eight laws learned the hard way, and ten decision records that shape Aurora.",
  canonical: routes.principles,
});

/** Doc slugs for the decision records, as named in reference/decisions/. */
const decisionDocs: Record<string, string> = {
  "0001": "reference/decisions/0001-two-storage-primitives",
  "0002": "reference/decisions/0002-files-are-the-durable-copy",
  "0003": "reference/decisions/0003-never-rewrite-the-record",
  "0004": "reference/decisions/0004-the-bus-is-disposable",
  "0005": "reference/decisions/0005-no-file-ownership",
  "0006": "reference/decisions/0006-deterministic-by-default",
  "0007": "reference/decisions/0007-union-not-consensus",
  "0008": "reference/decisions/0008-park-peer-mail",
  "0009": "reference/decisions/0009-charter-means-standing-contract",
  "0010": "reference/decisions/0010-generate-status-never-hand-write-it",
};

export default function PrinciplesPage() {
  return (
    <>
      <PageHero
        backdrop="lattice"
        eyebrow="Principles"
        title={
          <>
            Each habit came from a real mistake.
            <span className="text-mk-muted">
              {" "}
              Scripts enforce the important ones.
            </span>
          </>
        }
        description="Nine working ideas, eight laws learned from real incidents, and ten decision records that explain the choices you will notice first."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <HudFrame>
            <div className="hud-scanlines grid gap-px sm:grid-cols-3">
              {principles.map((principle, index) => (
                <Reveal key={principle} delay={index * 0.03}>
                  <div className="flex h-full flex-col gap-3 p-7">
                    <span className="font-hud text-hud-gold text-[12px] font-semibold tracking-[0.14em]">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="text-[19px] leading-snug font-medium tracking-tight text-white">
                      {principle}
                    </span>
                  </div>
                </Reveal>
              ))}
            </div>
          </HudFrame>
        </Container>
      </Section>

      <Section backdrop="nebula">
        <Container>
          <SectionIntro
            eyebrow="Laws"
            title="Laws learned the hard way"
            description="Each began as a real incident, became a lesson, and some became code. These are the fleet's own laws, not slogans."
          />
          <div
            id="laws"
            className="mt-12 grid scroll-mt-28 gap-4 md:grid-cols-2"
          >
            {laws.map((law, index) => (
              <Reveal key={law.phrase} delay={index * 0.03} className="h-full">
                <article className="mk-card flex h-full flex-col gap-3 p-6 sm:p-7">
                  <span className="font-hud text-hud-gold text-[9.5px] font-semibold tracking-[0.18em]">
                    House law
                  </span>
                  <h3 className="text-[19px] leading-snug font-medium tracking-tight text-white">
                    &ldquo;{law.phrase}&rdquo;
                  </h3>
                  <p className="text-mk-muted text-[14.5px] leading-relaxed">
                    {law.story}
                  </p>
                  <span className="text-mk-faint mt-auto font-mono text-[10.5px]">
                    {law.source}
                  </span>
                </article>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section backdrop="network">
        <Container>
          <SectionIntro
            eyebrow="Decision records"
            title="Ten decisions, and why"
            description="All accepted. Each one links to the full record with its context and consequences."
            action={<HudBadge>All accepted</HudBadge>}
          />
          <div className="mt-12 flex flex-col divide-y divide-white/[0.07] border-y border-white/[0.07]">
            {decisions.map((decision) => (
              <article
                key={decision.id}
                id={`adr-${decision.id}`}
                className="grid scroll-mt-28 gap-4 py-8 md:grid-cols-[120px_minmax(0,1fr)_minmax(0,1fr)] md:gap-8"
              >
                <span className="font-hud text-hud-gold text-[13px] font-semibold tracking-[0.14em]">
                  ADR {decision.id}
                </span>
                <div className="flex flex-col gap-2">
                  <h3 className="text-[22px] font-medium tracking-tight text-white">
                    {decision.title}
                  </h3>
                  <p className="text-mk-muted text-[15.5px] leading-relaxed">
                    {decision.belief}
                  </p>
                </div>
                <div className="flex flex-col justify-between gap-4">
                  {decision.quote ? (
                    <blockquote className="border-l border-white/15 pl-4 text-[15px] text-white/80 italic">
                      &ldquo;{decision.quote}&rdquo;
                    </blockquote>
                  ) : (
                    <span />
                  )}
                  <a
                    href={links.doc(
                      decisionDocs[decision.id] ?? "reference/decisions",
                    )}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-mk-faint inline-flex w-fit items-center gap-1 font-mono text-[11px] hover:text-white"
                  >
                    Read the record <ArrowUpRight className="size-3" />
                  </a>
                </div>
              </article>
            ))}
          </div>
          <div className="mt-10 flex items-center gap-3">
            <HudLabel tone="muted">Source</HudLabel>
            <span className="text-mk-faint font-mono text-[12px]">
              docs/reference/decisions · docs/concepts/method/principles
            </span>
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
