import { getMetadata } from "~/lib/metadata";
import { routes } from "~/modules/marketing/content/site";
import { bets, useCases } from "~/modules/marketing/content/use-cases";
import { LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";
import { FitCheck } from "~/modules/marketing/use-cases/fit-check";

export const generateMetadata = getMetadata({
  title: "Use cases",
  description:
    "Aurora is built for accumulation, not parallelism: long-lived work with persistent peers that inherit judgement. Here is where that pays off first.",
  canonical: routes.useCases,
});

export default function UseCasesPage() {
  return (
    <>
      <PageHero
        eyebrow="Use cases"
        title={
          <>
            Built for accumulation,
            <span className="text-mk-muted"> not parallelism.</span>
          </>
        }
        description="Aurora assumes the same peers work with you for a long time and inherit judgement. If you want disposable workers that start fresh every time, a queue may suit you better."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <div className="grid gap-4 lg:grid-cols-2">
            {bets.map((bet, index) => (
              <Reveal key={bet.id} delay={index * 0.06} className="h-full">
                <div
                  className={
                    bet.id === "accumulation"
                      ? "mk-card border-hud-cyan/25 flex h-full flex-col gap-4 p-7 sm:p-9"
                      : "mk-card flex h-full flex-col gap-4 p-7 sm:p-9"
                  }
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-hud text-hud-gold text-[11px] font-semibold tracking-[0.16em] uppercase">
                      {bet.title}
                    </span>
                    <span className="text-mk-faint font-mono text-[11px]">
                      {bet.id === "accumulation" ? "Aurora" : "other systems"}
                    </span>
                  </div>
                  <h2 className="mk-title text-2xl sm:text-[1.9rem]">
                    {bet.line}
                  </h2>
                  <p className="text-mk-muted text-[15px] leading-relaxed">
                    {bet.body}
                  </p>
                  <ul className="mt-auto flex flex-col gap-2 border-t border-white/[0.06] pt-5">
                    {bet.fits.map((fit) => (
                      <li
                        key={fit}
                        className="flex gap-2.5 text-[13.5px] leading-relaxed text-white/75"
                      >
                        <span
                          aria-hidden
                          className={
                            bet.id === "accumulation"
                              ? "bg-hud-cyan mt-[7px] size-1 shrink-0 rounded-full"
                              : "mt-[7px] size-1 shrink-0 rounded-full bg-white/30"
                          }
                        />
                        {fit}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal className="mt-8">
            <p className="text-mk-faint border-l border-white/10 pl-4 text-[14px] leading-relaxed">
              Aurora picks one side of that bet. Persistent peers on a shared
              bus inherit judgement, so a lesson one seat pays for surfaces for
              the next agent standing in the same place. That is why the pages
              below are about long-lived work, not bigger fan-out.
            </p>
          </Reveal>
        </Container>
      </Section>

      <Section backdrop="network">
        <Container>
          <SectionIntro
            eyebrow="Where it pays off"
            title="Five setups, one long-lived team"
            description="Each one assumes the same peers keep working on the same record. The second agent is where the memory starts to pay for itself."
          />
          <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {useCases.map((useCase, index) => (
              <Reveal
                key={useCase.slug}
                delay={index * 0.05}
                className="h-full"
              >
                <LinkCard
                  href={routes.useCase(useCase.slug)}
                  eyebrow={useCase.persona}
                  title={useCase.title}
                  description={useCase.summary}
                  className="h-full"
                >
                  <ul className="mb-3 flex flex-col gap-1.5">
                    {useCase.pains.map((pain) => (
                      <li
                        key={pain}
                        className="text-mk-faint flex gap-2 text-[13px]"
                      >
                        <span className="text-hud-red">×</span> {pain}
                      </li>
                    ))}
                  </ul>
                </LinkCard>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section backdrop="caustics">
        <Container>
          <SectionIntro
            eyebrow="Is it for you?"
            title="Five questions, an honest answer"
            description="Aurora is not for everyone. If you want disposable workers rather than persistent peers, we will say so."
          />
          <div className="mt-12">
            <FitCheck />
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
