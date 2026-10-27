import { match } from "@formatjs/intl-localematcher";
import dayjs from "dayjs";
import { createInstance } from "i18next";
import resourcesToBackend from "i18next-resources-to-backend";
import Negotiator from "negotiator";
import { initReactI18next } from "react-i18next/initReactI18next";
import * as z from "zod";

import { config, getInitOptions } from "../config";
import { env } from "../env";
import { isLocaleSupported, loadTranslation, makeZodI18nMap } from "../utils";

import type { i18n, Namespace, TFunction } from "i18next";

const getDefaultLocale = () =>
  isLocaleSupported(env.DEFAULT_LOCALE)
    ? env.DEFAULT_LOCALE
    : config.defaultLocale;

export const initializeServerI18n = async ({
  locale,
  defaultLocale,
  ns,
}: {
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
}): Promise<i18n> => {
  const i18n = createInstance();
  const loadedNamespaces = new Set<string>();

  await new Promise((resolve) => {
    void i18n
      .use(
        resourcesToBackend(
          async (
            language: (typeof config.locales)[number],
            namespace: (typeof config.namespaces)[number],
            callback,
          ) => {
            const data = await loadTranslation(language, namespace);

            loadedNamespaces.add(namespace);
            return callback(null, data);
          },
        ),
      )
      .use({
        type: "3rdParty",
        init: async (i18next: typeof i18n) => {
          let iterations = 0;
          const maxIterations = 100;

          while (i18next.isInitializing) {
            iterations++;

            if (iterations > maxIterations) {
              console.error(
                `i18next is not initialized after ${maxIterations} iterations`,
              );

              break;
            }

            await new Promise((resolve) => setTimeout(resolve, 1));
          }

          initReactI18next.init(i18next);
          resolve(i18next);
        },
      })
      .init(getInitOptions({ locale, defaultLocale, ns }));
  });

  const namespaces = ns
    ? typeof ns === "string"
      ? [ns]
      : ns
    : config.namespaces;

  // If all namespaces are already loaded, return the i18n instance
  if (loadedNamespaces.size === namespaces.length) {
    return i18n;
  }

  // Otherwise, wait for all namespaces to be loaded

  const maxWaitTimeMs = 100;
  const checkIntervalMs = 5;

  async function waitForNamespaces() {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTimeMs) {
      const allNamespacesLoaded = namespaces.every((ns) =>
        loadedNamespaces.has(ns),
      );

      if (allNamespacesLoaded) {
        return true;
      }

      await new Promise((resolve) => setTimeout(resolve, checkIntervalMs));
    }

    return false;
  }

  const success = await waitForNamespaces();

  if (!success) {
    console.warn(
      `Not all namespaces were loaded after ${maxWaitTimeMs}ms. Initialization may be incomplete.`,
    );
  }

  return i18n;
};

export const getLocaleFromCookies = async () => {
  try {
    const { cookies } = await import("next/headers");
    const locale = (await cookies()).get(config.cookie)?.value;
    return isLocaleSupported(locale) ? locale : undefined;
  } catch {
    return undefined;
  }
};

export const getLocaleFromRequest = (request?: Request) => {
  if (!request) return getDefaultLocale();

  const localeCookie = request.headers
    .get("cookie")
    ?.split(";")
    .find((cookie) => cookie.trim().startsWith(`${config.cookie}=`))
    ?.split("=")[1]
    ?.trim()
    .replace(/[.,]/g, "");

  if (isLocaleSupported(localeCookie)) {
    return localeCookie;
  }

  const negotiatorHeaders: Record<string, string> = {};
  request.headers.forEach((value: string, key: string) => {
    negotiatorHeaders[key] = value;
  });

  const languages = new Negotiator({ headers: negotiatorHeaders }).languages();

  try {
    return match(languages, config.locales, getDefaultLocale());
  } catch {
    return getDefaultLocale();
  }
};

export const getTranslation = async <T extends Namespace>({
  locale: passedLocale,
  request,
  ns,
}: { locale?: string; request?: Request; ns?: T } = {}) => {
  const requestedLocale =
    passedLocale ??
    (request ? getLocaleFromRequest(request) : null) ??
    (await getLocaleFromCookies()) ??
    getDefaultLocale();
  const locale = isLocaleSupported(requestedLocale)
    ? requestedLocale
    : config.defaultLocale;
  const i18nextInstance = await initializeServerI18n({
    locale,
    defaultLocale: getDefaultLocale(),
    ns,
  });
  dayjs.locale(i18nextInstance.language);

  const t = i18nextInstance.getFixedT<T>(
    i18nextInstance.language,
    ns,
  ) as TFunction<T>;

  z.config({
    localeError: makeZodI18nMap({ t: t as TFunction }),
  });

  return {
    t,
    i18n: i18nextInstance,
  };
};
