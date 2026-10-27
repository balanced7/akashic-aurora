import dayjs from "dayjs";
import { ArrowLeft, ArrowRight, ChevronRight } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  CollectionType,
  ContentStatus,
  getContentItemBySlug,
  getContentItems,
} from "@akashic-labs/cms";
import { SortOrder } from "@akashic-labs/shared/constants";

import { getMetadata } from "~/lib/metadata";
import { routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { Container } from "~/modules/marketing/ui/primitives";
import { ReadingProgress } from "~/modules/marketing/ui/reading-progress";
import { minutesToRead, walkLabel } from "~/modules/marketing/walks/meta";
import { MetaLine } from "~/modules/marketing/walks/meta-line";
import { getToc } from "~/modules/marketing/walks/toc";
import { WalkBody } from "~/modules/marketing/walks/walk-body";
import { WalkToc } from "~/modules/marketing/walks/walk-toc";

const getWalks = (locale?: string) =>
  getContentItems({
    collection: CollectionType.WALK,
    status: ContentStatus.PUBLISHED,
    sortBy: "walk",
    sortOrder: SortOrder.ASCENDING,
    locale,
  }).items;

export default async function WalkPage({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const { slug, locale } = await params;
  const walk = getContentItemBySlug({
    collection: CollectionType.WALK,
    slug,
    locale,
  });
  if (!walk) notFound();

  const walks = getWalks(locale);
  const index = walks.findIndex((item) => item.slug === walk.slug);
  const previous = walks[index - 1];
  const next = walks[index + 1];
  const toc = getToc(walk.content);

  return (
    <>
      <ReadingProgress />
      <article className="pt-32 pb-16 sm:pt-40">
        <Container className="max-w-6xl">
          <nav aria-label="Breadcrumb" className="mb-10">
            <ol className="text-mk-faint flex flex-wrap items-center gap-1.5 text-[13px]">
              <li>
                <Link href={routes.walks} className="hover:text-white">
                  Forest Walks
                </Link>
              </li>
              <li className="flex items-center gap-1.5">
                <ChevronRight className="size-3.5" />
                <span aria-current="page">{walkLabel(walk.walk)}</span>
              </li>
            </ol>
          </nav>

          <header className="flex max-w-4xl flex-col gap-5">
            <MetaLine
              items={[
                <span key="walk" className="text-hud-gold font-medium">
                  {walkLabel(walk.walk)}
                </span>,
                ...(walk.edition ? [walk.edition] : []),
                <time key="date" dateTime={walk.publishedAt.toISOString()}>
                  {dayjs(walk.publishedAt).format("MMMM D, YYYY")}
                </time>,
                <span key="time" data-testid="walk-reading-time">
                  {minutesToRead(walk.timeToRead)} min read
                </span>,
              ]}
            />
            <h1
              data-testid="page-title"
              className="mk-display text-[2.4rem] text-balance sm:text-6xl"
            >
              {walk.title}
            </h1>
            <p className="text-mk-muted max-w-[60ch] text-xl leading-relaxed text-pretty">
              {walk.description}
            </p>
          </header>

          <div className="mt-12 border-t border-white/[0.07] pt-10 lg:grid lg:grid-cols-[minmax(0,68ch)_minmax(0,1fr)] lg:gap-16 xl:gap-24">
            <div className="min-w-0">
              {toc.length > 2 && (
                <div className="mb-10 lg:hidden">
                  <WalkToc entries={toc} variant="inline" />
                </div>
              )}
              <WalkBody mdx={walk.mdx} />
            </div>
            {toc.length > 2 && (
              <aside className="hidden max-w-64 lg:block">
                <WalkToc entries={toc} variant="rail" />
              </aside>
            )}
          </div>

          {(previous ?? next) && (
            <nav
              aria-label="More walks"
              className="mt-20 grid max-w-[68ch] gap-4 border-t border-white/[0.07] pt-10 sm:grid-cols-2"
            >
              {previous && (
                <Link
                  href={routes.walk(previous.slug)}
                  className="mk-card mk-card-hover group flex flex-col gap-2 p-6"
                >
                  <span className="text-mk-faint flex items-center gap-1.5 text-[13px]">
                    <ArrowLeft className="size-3.5" />
                    {walkLabel(previous.walk)}
                  </span>
                  <span className="text-[17px] font-medium text-white">
                    {previous.title}
                  </span>
                </Link>
              )}
              {next && (
                <Link
                  href={routes.walk(next.slug)}
                  className="mk-card mk-card-hover group flex flex-col gap-2 p-6 sm:col-start-2 sm:text-right"
                >
                  <span className="text-mk-faint flex items-center gap-1.5 text-[13px] sm:justify-end">
                    {walkLabel(next.walk)}
                    <ArrowRight className="size-3.5" />
                  </span>
                  <span className="text-[17px] font-medium text-white">
                    {next.title}
                  </span>
                </Link>
              )}
            </nav>
          )}
        </Container>
      </article>

      <CtaBand />
    </>
  );
}

/** Every valid slug is known at build time; anything else is a real 404. */
export const dynamicParams = false;

export function generateStaticParams() {
  return getWalks().map((walk) => ({ slug: walk.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const { slug, locale } = await params;
  const walk = getContentItemBySlug({
    collection: CollectionType.WALK,
    slug,
    locale,
  });
  if (!walk) return {};
  return getMetadata({
    title: `Forest Walks: ${walk.title}`,
    description: walk.description,
    canonical: routes.walk(walk.slug),
    type: "article",
  })({ params });
}
