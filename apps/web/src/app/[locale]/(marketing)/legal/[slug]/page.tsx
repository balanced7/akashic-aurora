import { notFound } from "next/navigation";

import {
  CollectionType,
  getContentItemBySlug,
  getContentItems,
} from "@akashic-labs/cms";

import { getMetadata } from "~/lib/metadata";
import { ArticleBody } from "~/modules/marketing/ui/article-body";
import { Container, Eyebrow } from "~/modules/marketing/ui/primitives";

interface PageParams {
  params: Promise<{ slug: string; locale: string }>;
}

export default async function LegalPage({ params }: PageParams) {
  const { slug, locale } = await params;
  const item = getContentItemBySlug({
    collection: CollectionType.LEGAL,
    slug,
    locale,
  });
  if (!item) notFound();

  return (
    <article className="pt-32 pb-24 sm:pt-40">
      <Container className="max-w-3xl">
        <header className="flex flex-col gap-4 border-b border-white/[0.07] pb-10">
          <Eyebrow>Legal</Eyebrow>
          <h1
            data-testid="page-title"
            className="mk-display text-4xl sm:text-5xl"
          >
            {item.title}
          </h1>
          <p className="text-mk-muted text-lg">{item.description}</p>
        </header>
        <div className="mt-10">
          <ArticleBody mdx={item.mdx} />
        </div>
      </Container>
    </article>
  );
}

export function generateStaticParams() {
  return getContentItems({ collection: CollectionType.LEGAL }).items.map(
    ({ slug, locale }) => ({ slug, locale }),
  );
}

export async function generateMetadata({ params }: PageParams) {
  const { slug, locale } = await params;
  const item = getContentItemBySlug({
    collection: CollectionType.LEGAL,
    slug,
    locale,
  });
  if (!item) return {};
  return getMetadata({ title: item.title, description: item.description })({
    params,
  });
}
