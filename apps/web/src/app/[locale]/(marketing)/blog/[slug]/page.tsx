import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  CollectionType,
  ContentStatus,
  getContentItemBySlug,
  getContentItems,
} from "@akashic-labs/cms";
import { SortOrder } from "@akashic-labs/shared/constants";

import { pathsConfig } from "~/config/paths";
import { getMetadata } from "~/lib/metadata";
import { routes } from "~/modules/marketing/content/site";
import { ArticleBody } from "~/modules/marketing/ui/article-body";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudLabel } from "~/modules/marketing/ui/hud";
import { Container } from "~/modules/marketing/ui/primitives";
import { ReadingProgress } from "~/modules/marketing/ui/reading-progress";
import { ShaderBackground } from "~/modules/marketing/ui/shader-background";

dayjs.extend(duration);

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const { slug, locale } = await params;
  const item = getContentItemBySlug({
    collection: CollectionType.BLOG,
    slug,
    locale,
  });
  if (!item) notFound();

  const more = getContentItems({
    collection: CollectionType.BLOG,
    status: ContentStatus.PUBLISHED,
    sortBy: "publishedAt",
    sortOrder: SortOrder.DESCENDING,
    locale,
  }).items.filter((post) => post.slug !== item.slug);

  return (
    <>
      <ReadingProgress />
      <article className="relative isolate pt-32 pb-16 sm:pt-40">
        <ShaderBackground preset="nebula" fade="bottom" className="h-[560px]" />
        <Container className="max-w-3xl">
          <nav
            aria-label="Breadcrumb"
            className="text-mk-faint mb-10 text-[13px]"
          >
            <Link href={routes.blog} className="hover:text-white">
              Blog
            </Link>
          </nav>
          <header className="flex flex-col gap-5">
            <span className="text-mk-faint flex items-center gap-2 text-[13px]">
              <time dateTime={item.publishedAt.toISOString()}>
                {dayjs(item.publishedAt).format("MMMM D, YYYY")}
              </time>
              <span>·</span>
              <span>
                {Math.max(
                  1,
                  Math.ceil(dayjs.duration(item.timeToRead).asMinutes()),
                )}{" "}
                min read
              </span>
            </span>
            <h1
              data-testid="page-title"
              className="mk-display text-4xl sm:text-6xl"
            >
              {item.title}
            </h1>
            <p className="text-mk-muted text-xl leading-relaxed">
              {item.description}
            </p>
          </header>
          <div className="mt-10 overflow-hidden rounded-[22px] border border-white/[0.08]">
            {/* eslint-disable-next-line @next/next/no-img-element -- local SVG cover art */}
            <img
              src={item.thumbnail}
              alt=""
              className="aspect-[3/2] w-full object-cover"
            />
          </div>
          <div className="mt-12">
            <ArticleBody mdx={item.mdx} />
          </div>
        </Container>
      </article>

      {more.length > 0 && (
        <section className="pb-16">
          <Container className="max-w-3xl">
            <HudLabel tone="muted">Keep reading</HudLabel>
            <div className="mt-4 flex flex-col divide-y divide-white/[0.07] border-y border-white/[0.07]">
              {more.slice(0, 3).map((post) => (
                <Link
                  key={post.slug}
                  href={pathsConfig.marketing.blog.post(post.slug)}
                  className="group flex items-center justify-between gap-6 py-5"
                >
                  <span className="text-[17px] font-medium text-white group-hover:text-white/80">
                    {post.title}
                  </span>
                  <span className="text-mk-faint shrink-0 text-[13px]">
                    {dayjs(post.publishedAt).format("MMM D")}
                  </span>
                </Link>
              ))}
            </div>
          </Container>
        </section>
      )}

      <CtaBand />
    </>
  );
}

/** Every valid slug is known at build time; anything else is a real 404. */
export const dynamicParams = false;

export function generateStaticParams() {
  return getContentItems({ collection: CollectionType.BLOG }).items.map(
    (post) => ({ slug: post.slug }),
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const { slug, locale } = await params;
  const item = getContentItemBySlug({
    collection: CollectionType.BLOG,
    slug,
    locale,
  });
  if (!item) return {};
  return getMetadata({
    title: item.title,
    description: item.description,
    canonical: pathsConfig.marketing.blog.post(item.slug),
    type: "article",
  })({ params });
}
