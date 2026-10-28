import { isKey } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";

import { appConfig } from "~/config/app";

import type { TranslationKey } from "@akashic-labs/i18n";
import type { Metadata, Viewport } from "next";

type OpenGraphType =
  | "article"
  | "book"
  | "music.song"
  | "music.album"
  | "music.playlist"
  | "music.radio_station"
  | "profile"
  | "website"
  | "video.tv_show"
  | "video.other"
  | "video.movie"
  | "video.episode";

interface SeoProps {
  readonly title?: TranslationKey | (string & Record<never, never>);
  readonly description?: TranslationKey | (string & Record<never, never>);
  readonly image?: string;
  readonly url?: string;
  readonly canonical?: string;
  readonly type?: OpenGraphType;
  readonly images?: {
    url: string;
    width: number;
    height: number;
    alt?: string;
  }[];
}

const SITE_NAME_SEPARATOR = " | ";
export const SITE_NAME_TEMPLATE = `%s${SITE_NAME_SEPARATOR}${appConfig.name}`;

const DEFAULT_IMAGE = {
  url: `${appConfig.url}/opengraph-image.png`,
  width: 1200,
  height: 630,
  alt: appConfig.name,
};

/** "Bifrost: Agents mail each other" becomes eyebrow "Bifrost" and title "Agents mail each other". */
const socialCard = (title: string) => {
  const [head, ...rest] = title.split(": ");
  const hasEyebrow = rest.length > 0 && (head?.length ?? 0) <= 32;
  const eyebrow = hasEyebrow ? (head ?? appConfig.name) : appConfig.name;
  const body = hasEyebrow ? rest.join(": ") : title;
  const text = body.charAt(0).toUpperCase() + body.slice(1);
  const params = new URLSearchParams({ title: text, eyebrow });
  return {
    url: `${appConfig.url}/api/og?${params.toString()}`,
    width: 1200,
    height: 630,
    alt: title,
  };
};

export const getMetadata =
  (
    {
      title,
      description = "A home for your agents: shared memory, a message bus and a trust layer for a team of AI agents and one human.",
      url,
      canonical,
      images,
      type = "website",
    } = {} as SeoProps,
  ) =>
  async ({
    params,
  }: {
    params?: Promise<{ locale: string }>;
  }): Promise<Metadata> => {
    const { t, i18n } = await getTranslation({
      locale: (await params)?.locale,
    });

    const resolvedTitle =
      title && (isKey(title, i18n) ? (t(title) as string) : title);
    const common = {
      ...(resolvedTitle && { title: resolvedTitle }),
      description: isKey(description, i18n)
        ? (t(description) as string)
        : description,
    };

    // Pages with a title get their own social card unless they pass images explicitly.
    const cardImages =
      images ?? (resolvedTitle ? [socialCard(resolvedTitle)] : [DEFAULT_IMAGE]);

    return {
      ...common,
      openGraph: {
        ...common,
        url: url ?? canonical ?? appConfig.url,
        siteName: appConfig.name,
        type,
        images: cardImages,
      },
      ...{
        ...(canonical && {
          alternates: {
            canonical,
          },
        }),
      },
      twitter: {
        card: "summary_large_image" as const,
        images: cardImages,
      },
    };
  };

export const DEFAULT_METADATA: Metadata = {
  ...(await getMetadata()({
    params: Promise.resolve({ locale: appConfig.locale }),
  })),
  title: {
    template: SITE_NAME_TEMPLATE,
    default: appConfig.name,
  },
  metadataBase: appConfig.url ? new URL(appConfig.url) : null,
};

export const DEFAULT_VIEWPORT: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#030712" },
  ],
};
