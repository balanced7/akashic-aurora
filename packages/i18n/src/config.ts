import { env } from "./env";

import type { InitOptions, Namespace } from "i18next";

const locales = ["en", "sl", "nb"] as const;
type SupportedLocale = (typeof locales)[number];

const isSupportedLocale = (locale?: string): locale is SupportedLocale =>
  locale !== undefined && locales.includes(locale as SupportedLocale);

export const config = {
  locales,
  defaultLocale: isSupportedLocale(env.NEXT_PUBLIC_DEFAULT_LOCALE)
    ? env.NEXT_PUBLIC_DEFAULT_LOCALE
    : "en",
  namespaces: [
    "common",
    "admin",
    "organization",
    "dashboard",
    "auth",
    "billing",
    "marketing",
    "validation",
    "reports",
  ],
  cookie: "locale",
} as const;

export const getInitOptions = ({
  locale,
  defaultLocale,
  ns,
}: {
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
}): InitOptions => ({
  supportedLngs: config.locales,
  fallbackLng: isSupportedLocale(defaultLocale)
    ? defaultLocale
    : config.defaultLocale,
  lng: isSupportedLocale(locale) ? locale : undefined,
  defaultNS: config.namespaces,
  fallbackNS: config.namespaces,
  ns: ns ?? config.namespaces,
  preload: false,
  interpolation: {
    escapeValue: false,
  },
  missingInterpolationHandler: (text, value, options) => {
    console.debug(
      `Missing interpolation value for key: ${text}`,
      value,
      options,
    );
  },
});
