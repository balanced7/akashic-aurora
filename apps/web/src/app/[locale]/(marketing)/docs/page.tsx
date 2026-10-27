import { Search } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import { docSections } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { DocCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
} from "~/modules/marketing/ui/primitives";

export const generateMetadata = getMetadata({
  title: "Docs",
  description:
    "Aurora documentation: quickstart, a ten-minute tutorial, eight how-to guides, seven concept sections and the reference.",
  canonical: routes.docs,
});

export default async function DocsPage(props: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await props.searchParams;
  // Match "handoff", "hand off" and "hand-off" alike.
  const normalize = (text: string) =>
    text.toLowerCase().replace(/[^a-z0-9]+/g, "");
  const needle = normalize(q);
  const sections = docSections
    .map((section) => ({
      ...section,
      pages: section.pages.filter(
        (page) =>
          !needle ||
          normalize(`${page.title} ${page.summary} ${page.path}`).includes(
            needle,
          ),
      ),
    }))
    .filter((section) => section.pages.length > 0);

  return (
    <>
      <PageHero
        eyebrow="Docs"
        title={
          <>
            Learn Aurora
            <span className="text-mk-muted"> at your own depth</span>
          </>
        }
        description="Start with a two-minute quickstart. Go deeper with how-to guides, concepts and the reference. Every page is written in plain words."
        actions={
          <>
            <ButtonLink href={links.doc("quickstart")} size="lg" arrow>
              Quickstart
            </ButtonLink>
            <ButtonLink href={links.docs} variant="secondary" size="lg" arrow>
              Open the docs site
            </ButtonLink>
          </>
        }
      >
        <form action={routes.docs} className="relative max-w-xl">
          <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-white/55" />
          <input
            type="search"
            name="q"
            defaultValue={q}
            placeholder="Search topics, like recall or handoff"
            aria-label="Search docs topics"
            className="h-12 w-full rounded-xl border border-white/[0.1] bg-white/[0.04] pr-4 pl-11 text-[15px] text-white placeholder:text-white/50 focus:border-white/25 focus:outline-none"
          />
        </form>
      </PageHero>

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="flex flex-col gap-16">
          {sections.length === 0 && (
            <p className="text-mk-muted text-[16px]">
              No topics match &ldquo;{q}&rdquo;. Try a broader word.
            </p>
          )}
          {sections.map((section) => (
            <section
              key={section.title}
              data-testid="docs-section"
              className="flex flex-col gap-6"
            >
              <div className="flex flex-col gap-1.5">
                <h2 className="text-[26px] font-semibold tracking-tight text-white">
                  {section.title}
                </h2>
                <p className="text-mk-muted text-[15px]">
                  {section.description}
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {section.pages.map((page) => (
                  <DocCard
                    key={page.path || "index"}
                    title={page.title}
                    path={page.path}
                    summary={page.summary}
                  />
                ))}
              </div>
            </section>
          ))}
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
