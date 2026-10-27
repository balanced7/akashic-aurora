import { CollectionType, getContentItems } from "@akashic-labs/cms";
import { getPathname, config } from "@akashic-labs/i18n";

import { appConfig } from "~/config/app";
import { pathsConfig } from "~/config/paths";
import { pillars } from "~/modules/marketing/content/aurora";
import { integrations } from "~/modules/marketing/content/integrations";
import { routes } from "~/modules/marketing/content/site";
import { useCases } from "~/modules/marketing/content/use-cases";

import type { MetadataRoute } from "next";

const url = (path: string) => `${appConfig.url}${path}`;

const getEntry = (path: string) => ({
  url: url(
    getPathname({
      path,
      locale: appConfig.locale,
      defaultLocale: appConfig.locale,
    }),
  ),
  alternates: {
    languages: Object.fromEntries(
      config.locales.map((locale) => [
        locale,
        url(
          getPathname({
            path,
            locale,
            defaultLocale: appConfig.locale,
          }),
        ),
      ]),
    ),
  },
});

const marketingPages = [
  routes.aurora,
  routes.howItWorks,
  routes.useCases,
  routes.integrations,
  routes.compare,
  routes.evidence,
  routes.principles,
  routes.openSource,
  routes.security,
  routes.enterprise,
  routes.changelog,
  routes.docs,
  routes.glossary,
  routes.about,
  ...pillars.map((pillar) => routes.pillar(pillar.slug)),
  ...useCases.map((useCase) => routes.useCase(useCase.slug)),
  ...integrations.map(
    (integration) => `${routes.integrations}/${integration.slug}`,
  ),
];

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      ...getEntry(pathsConfig.index),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 1,
    },
    ...marketingPages.map<MetadataRoute.Sitemap[number]>((path) => ({
      ...getEntry(path),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    })),
    {
      ...getEntry(pathsConfig.marketing.pricing),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      ...getEntry(pathsConfig.marketing.contact),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      ...getEntry(pathsConfig.marketing.blog.index),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    ...getContentItems({
      collection: CollectionType.BLOG,
      locale: appConfig.locale,
    }).items.map<MetadataRoute.Sitemap[number]>((post) => ({
      ...getEntry(pathsConfig.marketing.blog.post(post.slug)),
      lastModified: new Date(post.lastModifiedAt),
      changeFrequency: "monthly",
      priority: 0.7,
    })),
    {
      ...getEntry(routes.walks),
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    ...getContentItems({
      collection: CollectionType.WALK,
      locale: appConfig.locale,
    }).items.map<MetadataRoute.Sitemap[number]>((walk) => ({
      ...getEntry(routes.walk(walk.slug)),
      lastModified: new Date(walk.lastModifiedAt),
      changeFrequency: "monthly",
      priority: 0.7,
    })),
    ...getContentItems({
      collection: CollectionType.LEGAL,
      locale: appConfig.locale,
    }).items.map<MetadataRoute.Sitemap[number]>((post) => ({
      ...getEntry(pathsConfig.marketing.legal(post.slug)),
      lastModified: new Date(post.lastModifiedAt),
      changeFrequency: "yearly",
      priority: 0.5,
    })),
  ];
}
