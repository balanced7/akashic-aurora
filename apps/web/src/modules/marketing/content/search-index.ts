import {
  CollectionType,
  ContentStatus,
  getContentItems,
} from "@akashic-labs/cms";

import { pathsConfig } from "~/config/paths";
import {
  docSections,
  glossary,
  pillars,
} from "~/modules/marketing/content/aurora";
import { integrations } from "~/modules/marketing/content/integrations";
import {
  links,
  navGroups,
  navLinks,
  routes,
} from "~/modules/marketing/content/site";
import { useCases } from "~/modules/marketing/content/use-cases";

export interface SearchEntry {
  readonly title: string;
  readonly description: string;
  readonly href: string;
  readonly group:
    | "Pages"
    | "Aurora"
    | "Concepts"
    | "Docs"
    | "Glossary"
    | "Blog";
  readonly keywords?: string;
}

/** Everything the command palette can find. Built on the server, sent once with the layout. */
export const buildSearchIndex = (locale: string): SearchEntry[] => {
  const pages: SearchEntry[] = [
    {
      title: "Home",
      description: "A home for your agents",
      href: routes.home,
      group: "Pages",
    },
    ...navGroups.flatMap((group) =>
      group.items.map((item) => ({
        title: item.title,
        description: item.description,
        href: item.href,
        group: "Pages" as const,
      })),
    ),
    ...navLinks.map((item) => ({
      title: item.label,
      description: "",
      href: item.href,
      group: "Pages" as const,
    })),
    {
      title: "About",
      description: "Akashic Labs and how we work",
      href: routes.about,
      group: "Pages",
    },
    {
      title: "Contact",
      description: "Talk to the people who build Aurora",
      href: routes.contact,
      group: "Pages",
    },
    ...useCases.map((useCase) => ({
      title: useCase.title,
      description: useCase.persona,
      href: routes.useCase(useCase.slug),
      group: "Pages" as const,
    })),
    ...integrations.map((integration) => ({
      title: `Aurora for ${integration.name}`,
      description: integration.tagline,
      href: `${routes.integrations}/${integration.slug}`,
      group: "Pages" as const,
      keywords: integration.name,
    })),
  ];

  const aurora: SearchEntry[] = pillars.map((pillar) => ({
    title: pillar.name,
    description: pillar.title,
    href: routes.pillar(pillar.slug),
    group: "Aurora",
  }));

  const concepts: SearchEntry[] = pillars.flatMap((pillar) =>
    pillar.concepts.map((concept) => ({
      title: concept.name,
      description: concept.body,
      href: routes.pillar(pillar.slug),
      group: "Concepts" as const,
      keywords: pillar.name,
    })),
  );

  const docs: SearchEntry[] = docSections.flatMap((section) =>
    section.pages.map((page) => ({
      title: page.title,
      description: page.summary,
      href: links.doc(page.path),
      group: "Docs" as const,
      keywords: section.title,
    })),
  );

  const terms: SearchEntry[] = glossary.map((item) => ({
    title: item.term,
    description: item.definition,
    href: `${routes.glossary}#${item.term
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "")}`,
    group: "Glossary",
  }));

  const posts: SearchEntry[] = getContentItems({
    collection: CollectionType.BLOG,
    status: ContentStatus.PUBLISHED,
    locale,
  }).items.map((post) => ({
    title: post.title,
    description: post.description,
    href: pathsConfig.marketing.blog.post(post.slug),
    group: "Blog",
  }));

  // De-duplicate by href + title (nav groups repeat a few pages).
  const seen = new Set<string>();
  return [...pages, ...aurora, ...concepts, ...docs, ...terms, ...posts].filter(
    (entry) => {
      const key = `${entry.href}|${entry.title}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    },
  );
};
