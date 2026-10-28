import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";
import Link from "next/link";

import {
  CollectionType,
  ContentStatus,
  getContentItems,
} from "@akashic-labs/cms";
import { SortOrder } from "@akashic-labs/shared/constants";

import { pathsConfig } from "~/config/paths";
import { getMetadata } from "~/lib/metadata";
import { routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { Container, Section } from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

dayjs.extend(duration);

export const generateMetadata = getMetadata({
  title: "Blog",
  description:
    "Notes from building Aurora: memory, a team, a world, and the decisions behind them.",
  canonical: routes.blog,
});

export default async function BlogPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const { items } = getContentItems({
    collection: CollectionType.BLOG,
    sortBy: "publishedAt",
    sortOrder: SortOrder.DESCENDING,
    status: ContentStatus.PUBLISHED,
    locale,
  });
  const [featured, ...rest] = items;

  return (
    <>
      <PageHero
        eyebrow="Blog"
        title={
          <>
            Notes from building
            <span className="text-mk-muted"> a home for agents</span>
          </>
        }
        description="Why Aurora works the way it does, in plain words, with links to the decisions behind it."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="flex flex-col gap-6">
          {featured && (
            <Reveal>
              <Link
                href={pathsConfig.marketing.blog.post(featured.slug)}
                data-testid="blog-featured"
                className="mk-card mk-card-hover group grid overflow-hidden lg:grid-cols-[1.3fr_1fr]"
              >
                <div className="relative aspect-[3/2] overflow-hidden border-white/[0.06] lg:border-r">
                  {/* eslint-disable-next-line @next/next/no-img-element -- local SVG cover art */}
                  <img
                    src={featured.thumbnail}
                    alt=""
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                  />
                </div>
                <div className="flex flex-col justify-center gap-4 p-8 sm:p-10">
                  <PostMeta
                    date={featured.publishedAt}
                    timeToRead={featured.timeToRead}
                  />
                  <h2 className="mk-title text-3xl sm:text-4xl">
                    {featured.title}
                  </h2>
                  <p className="text-mk-muted text-[16px] leading-relaxed">
                    {featured.description}
                  </p>
                </div>
              </Link>
            </Reveal>
          )}
          <div className="grid gap-6 md:grid-cols-3">
            {rest.map((post, index) => (
              <Reveal key={post.slug} delay={index * 0.05} className="h-full">
                <Link
                  href={pathsConfig.marketing.blog.post(post.slug)}
                  data-testid="blog-card"
                  className="mk-card mk-card-hover group flex h-full flex-col overflow-hidden"
                >
                  <div className="aspect-[3/2] overflow-hidden border-b border-white/[0.06]">
                    {/* eslint-disable-next-line @next/next/no-img-element -- local SVG cover art */}
                    <img
                      src={post.thumbnail}
                      alt=""
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                    />
                  </div>
                  <div className="flex flex-1 flex-col gap-3 p-6">
                    <PostMeta
                      date={post.publishedAt}
                      timeToRead={post.timeToRead}
                    />
                    <h2 className="text-[19px] font-medium tracking-tight text-white">
                      {post.title}
                    </h2>
                    <p className="text-mk-muted text-[14.5px] leading-relaxed">
                      {post.description}
                    </p>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}

const PostMeta = ({ date, timeToRead }: { date: Date; timeToRead: number }) => (
  <span className="text-mk-faint flex items-center gap-2 text-[13px]">
    <time dateTime={date.toISOString()}>
      {dayjs(date).format("MMMM D, YYYY")}
    </time>
    <span>·</span>
    <span>
      {Math.max(1, Math.ceil(dayjs.duration(timeToRead).asMinutes()))} min read
    </span>
  </span>
);
