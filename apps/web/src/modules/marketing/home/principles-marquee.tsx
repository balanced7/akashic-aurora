import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { laws } from "~/modules/marketing/content/aurora";
import { routes } from "~/modules/marketing/content/site";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";

export const PrinciplesMarquee = () => (
  <Section className="overflow-hidden">
    <Container>
      <SectionIntro
        eyebrow="The culture"
        title={
          <>
            Laws learned
            <br />
            <span className="text-mk-muted">the hard way.</span>
          </>
        }
        description="Each one began as a real incident, became a lesson, and some became code. These are the fleet's own laws, not slogans."
        action={
          <Link
            href={`${routes.principles}#laws`}
            className="inline-flex items-center gap-1.5 text-[15px] font-medium text-white hover:text-white/70"
          >
            All of them <ArrowRight className="size-4" />
          </Link>
        }
      />
    </Container>
    <div className="mk-fade-x mt-14 overflow-hidden">
      <div className="animate-mk-marquee flex w-max gap-4 pr-4 [animation-duration:90s] hover:[animation-play-state:paused]">
        {[...laws, ...laws].map((law, index) => (
          <Link
            key={`${law.phrase}-${index}`}
            href={`${routes.principles}#laws`}
            aria-hidden={index >= laws.length}
            tabIndex={index >= laws.length ? -1 : undefined}
            className="mk-card mk-card-hover flex w-[360px] shrink-0 flex-col gap-4 p-6"
          >
            <span className="font-hud text-hud-gold text-[10px] font-semibold tracking-[0.18em]">
              House law
            </span>
            <span className="text-[20px] leading-snug font-medium tracking-tight text-white">
              &ldquo;{law.phrase}&rdquo;
            </span>
            <span className="text-mk-muted text-[14.5px] leading-relaxed">
              {law.story}
            </span>
            <span className="text-mk-faint mt-auto font-mono text-[10.5px]">
              {law.source}
            </span>
          </Link>
        ))}
      </div>
    </div>
  </Section>
);
