import { config } from "../config";
import { translations } from "../translations";

import type { TranslationKey } from "../client";
import type { DefaultNamespace, Namespace, i18n } from "i18next";

export const loadTranslation = async (
  locale: (typeof config.locales)[number],
  namespace: (typeof config.namespaces)[number],
) => {
  const localeTranslations = translations[locale];
  const load = (
    localeTranslations as Partial<
      Record<
        (typeof config.namespaces)[number],
        () => Promise<{ default: unknown }>
      >
    >
  )[namespace];

  // Locale hasn't translated this namespace yet - i18next falls back to `en`.
  if (!load) {
    return {};
  }

  try {
    const data = await load();

    return data.default as Record<string, unknown>;
  } catch {
    console.error(`Error while loading i18n file: ${locale}/${namespace}.json`);

    return {};
  }
};

/**
 * Every namespace for a locale, plus the default locale for fallbacks, shaped as i18next resources.
 * Server layouts pass this to I18nProvider so client components can render translated text on the server.
 */
export const loadResources = async (
  locale: (typeof config.locales)[number],
) => {
  const languages =
    locale === config.defaultLocale ? [locale] : [locale, config.defaultLocale];
  const entries = await Promise.all(
    languages.map(async (language) => {
      const namespaces = await Promise.all(
        config.namespaces.map(
          async (namespace) =>
            [namespace, await loadTranslation(language, namespace)] as const,
        ),
      );
      return [language, Object.fromEntries(namespaces)] as const;
    }),
  );
  return Object.fromEntries(entries) as Record<
    string,
    Record<string, Record<string, unknown>>
  >;
};

export const isKey = <T extends Namespace = DefaultNamespace>(
  key: string,
  i18n?: i18n,
  ns?: T,
): key is TranslationKey<T> => {
  return i18n?.exists(key, { ns }) ?? false;
};

export const isLocaleSupported = (
  locale?: string,
): locale is (typeof config.locales)[number] =>
  locale !== undefined &&
  config.locales.includes(locale as (typeof config.locales)[number]);

export const getPathname = ({
  locale,
  path,
  defaultLocale,
}: {
  locale: string;
  path: string;
  defaultLocale?: string;
}) => {
  const pathname = path.replace(
    new RegExp(`^/(${config.locales.join("|")})`),
    "",
  );

  if (locale === (defaultLocale ?? config.defaultLocale)) {
    return pathname.startsWith("/") ? pathname : `/${pathname}`;
  }

  return `/${locale}${pathname.startsWith("/") ? pathname : `/${pathname}`}`;
};

export * from "./validation";
