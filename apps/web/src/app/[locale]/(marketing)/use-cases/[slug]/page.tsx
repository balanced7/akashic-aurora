import { Check, X } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getMetadata } from "~/lib/metadata";
import { getPillar } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { getUseCase, useCases } from "~/modules/marketing/content/use-cases";
import { DocCard, LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
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
  return useCases.map((useCase) => ({ slug: useCase.slug }));
}

export async function generateMetadata(props: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const params = await props.params;
  const useCase = getUseCase(params.slug);
  if (!useCase) return {};
  return getMetadata({
    title: useCase.title,
    description: useCase.summary,
    canonical: routes.useCase(useCase.slug),
  })({ params: Promise.resolve({ locale: params.locale }) });
}

export default async function UseCasePage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;
  const useCase = getUseCase(slug);
  if (!useCase) notFound();
  const others = useCases
    .filter((item) => item.slug !== useCase.slug)
    .slice(0, 3);

  return (
    <>
      <PageHero
        crumbs={[
          { label: "Use cases", href: routes.useCases },
          { label: useCase.persona, href: routes.useCase(useCase.slug) },
        ]}
        eyebrow={useCase.persona}
        title={useCase.title}
        description={useCase.summary}
        actions={
          <ButtonLink href={links.doc("quickstart")} size="lg" arrow>
            Get started
          </ButtonLink>
        }
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="mk-card flex flex-col gap-4 p-7">
            <HudLabel tone="muted">The problem</HudLabel>
            <ul className="flex flex-col gap-3">
              {useCase.pains.map((pain) => (
                <li key={pain} className="text-mk-muted flex gap-3 text-[16px]">
                  <X className="text-hud-red mt-1 size-4 shrink-0" />
                  {pain}
                </li>
              ))}
            </ul>
          </div>
          <Terminal lines={useCase.terminal} title="aurora" caret />
        </div>
      </PageHero>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="How Aurora helps"
            title="Three parts do the heavy lifting"
          />
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {useCase.helps.map((help, index) => {
              const pillar = getPillar(help.pillar);
              return (
                <Reveal
                  key={help.title}
                  delay={index * 0.05}
                  className="h-full"
                >
                  <LinkCard
                    href={routes.pillar(help.pillar)}
                    eyebrow={pillar?.name}
                    title={help.title}
                    description={help.body}
                    className="h-full"
                  />
                </Reveal>
              );
            })}
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <SectionIntro
            eyebrow="An example run"
            title="What it looks like over time"
            description="A sketch of a typical run, using real Aurora verbs. Your timeline will differ."
          />
          <ol className="relative flex flex-col gap-0 border-l border-white/[0.1] pl-8">
            {useCase.timeline.map((item, index) => (
              <Reveal key={`${item.when}-${index}`} delay={index * 0.05}>
                <li className="relative pb-9 last:pb-0">
                  <span className="hud-gem absolute top-1.5 -left-[37px]" />
                  <span className="font-hud text-hud-gold text-[12px] font-semibold tracking-[0.14em] uppercase">
                    {item.when}
                  </span>
                  <p className="mt-1.5 text-[16.5px] leading-relaxed text-white/90">
                    {item.what}
                  </p>
                </li>
              </Reveal>
            ))}
          </ol>
        </Container>
      </Section>

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Before and after"
            title="What changes, and how it feels"
          />
          <div className="mt-12 overflow-x-auto rounded-[22px] border border-white/[0.08]">
            <table className="w-full min-w-[640px] text-left text-[15px]">
              <thead className="text-mk-faint bg-white/[0.02] text-[12px]">
                <tr>
                  <th className="px-6 py-3 font-medium">Moment</th>
                  <th className="px-6 py-3 font-medium">Before</th>
                  <th className="px-6 py-3 font-medium">With Aurora</th>
                  <th className="px-6 py-3 font-medium">Feeling</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {useCase.shifts.map((shift) => (
                  <tr key={shift.moment}>
                    <td className="px-6 py-4 font-medium text-white">
                      {shift.moment}
                    </td>
                    <td className="text-mk-faint px-6 py-4">{shift.before}</td>
                    <td className="px-6 py-4 text-white/85">
                      <span className="flex gap-2">
                        <Check className="text-hud-cyan mt-1 size-3.5 shrink-0" />
                        {shift.after}
                      </span>
                    </td>
                    <td className="font-hud text-hud-gold px-6 py-4 text-[12px] font-semibold tracking-[0.12em] uppercase">
                      {shift.feeling}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Container>
      </Section>

      <Section>
        <Container className="flex flex-col gap-10">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {useCase.docs.map((doc) => (
              <DocCard key={doc.path} title={doc.title} path={doc.path} />
            ))}
          </div>
          <div className="flex flex-col gap-4">
            <HudLabel tone="muted">More use cases</HudLabel>
            <div className="grid gap-4 md:grid-cols-3">
              {others.map((other) => (
                <Link
                  key={other.slug}
                  href={routes.useCase(other.slug)}
                  className="mk-card mk-card-hover flex flex-col gap-1 p-5"
                >
                  <span className="text-mk-faint text-[12px]">
                    {other.persona}
                  </span>
                  <span className="text-[16px] font-medium text-white">
                    {other.title}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
