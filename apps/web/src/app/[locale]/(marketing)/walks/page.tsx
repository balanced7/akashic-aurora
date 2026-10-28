import dayjs from "dayjs";
import Link from "next/link";

import {
  CollectionType,
  ContentStatus,
  getContentItems,
} from "@akashic-labs/cms";
import { SortOrder } from "@akashic-labs/shared/constants";

import { getMetadata } from "~/lib/metadata";
import { routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { Container, Section } from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";
import { minutesToRead, walkLabel } from "~/modules/marketing/walks/meta";
import { MetaLine } from "~/modules/marketing/walks/meta-line";

export const generateMetadata = getMetadata({
  title: "Forest Walks: How machines really work",
  description:
    "Long reads on how a computer works under the hood, from the memory wall to branch prediction. Every claim is sourced, and every walk ends with an exam.",
  canonical: routes.walks,
});

export default async function WalksPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const { items } = getContentItems({
    collection: CollectionType.WALK,
    status: ContentStatus.PUBLISHED,
    sortBy: "walk",
    sortOrder: SortOrder.ASCENDING,
    locale,
  });

  return (
    <>
      <PageHero
        eyebrow="Forest Walks"
        title={
          <>
            How machines really work,
            <span className="text-mk-muted"> one walk at a time</span>
          </>
        }
        description="Long reads on what a computer does under the hood. Every claim has a source, the mistakes are corrected in the open, and every walk ends with an exam. Predict before you look."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <ol className="flex max-w-4xl flex-col gap-5">
            {items.map((walk, index) => (
              <li key={walk.slug}>
                <Reveal delay={index * 0.05}>
                  <Link
                    href={routes.walk(walk.slug)}
                    data-testid="walk-card"
                    className="mk-card mk-card-hover group flex flex-col gap-4 p-7 sm:flex-row sm:gap-8 sm:p-9"
                  >
                    <span
                      aria-label={walkLabel(walk.walk)}
                      className="mk-display text-mk-faint shrink-0 text-5xl leading-none tabular-nums transition-colors group-hover:text-white/70 sm:w-20"
                    >
                      {String(walk.walk).padStart(2, "0")}
                    </span>
                    <span className="flex flex-col gap-3">
                      <MetaLine
                        items={[
                          ...(walk.edition ? [walk.edition] : []),
                          `${minutesToRead(walk.timeToRead)} min read`,
                          <time
                            key="date"
                            dateTime={walk.publishedAt.toISOString()}
                          >
                            {dayjs(walk.publishedAt).format("MMMM D, YYYY")}
                          </time>,
                        ]}
                      />
                      <h2 className="mk-title text-2xl text-balance sm:text-[28px]">
                        {walk.title}
                      </h2>
                      <p className="text-mk-muted text-[16px] leading-relaxed text-pretty">
                        {walk.description}
                      </p>
                    </span>
                  </Link>
                </Reveal>
              </li>
            ))}
          </ol>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
