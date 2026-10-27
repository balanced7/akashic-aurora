"use client";

import dayjs from "dayjs";
import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import resourcesToBackend from "i18next-resources-to-backend";
import { useEffect, useState } from "react";
import {
  I18nextProvider,
  initReactI18next,
  useTranslation as useTranslationBase,
} from "react-i18next";
import * as z from "zod";

import { getInitOptions, config } from "../config";
import { isLocaleSupported, loadTranslation, makeZodI18nMap } from "../utils";

import type {
  i18n,
  FlatNamespace,
  Namespace,
  KeyPrefix,
  Resource,
  TFunction,
} from "i18next";
import type { FallbackNs, UseTranslationOptions } from "react-i18next";

let client: i18n | null = null;

let iteration = 0;
const MAX_ITERATIONS = 20;

export const initializeI18nClient = async ({
  locale,
  defaultLocale,
  ns,
}: {
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
} = {}) => {
  if (client) {
    return client;
  }

  const loadedLanguages = new Set<string>();
  const loadedNamespaces = new Set<string>();
  const i18n = i18next.createInstance();

  await i18n
    .use(initReactI18next)
    .use(initReactI18next)
    .use(
      resourcesToBackend(
        async (
          language: (typeof config.locales)[number],
          namespace: (typeof config.namespaces)[number],
          callback,
        ) => {
          const data = await loadTranslation(language, namespace);

          if (!loadedLanguages.has(language)) {
            loadedLanguages.add(language);
          }

          if (!loadedNamespaces.has(namespace)) {
            loadedNamespaces.add(namespace);
          }

          return callback(null, data);
        },
      ),
    )
    .use(LanguageDetector)
    .init(
      {
        ...getInitOptions({
          locale,
          defaultLocale,
          ns,
        }),
        detection: {
          order: ["htmlTag", "cookie", "navigator"],
          caches: ["cookie"],
          lookupCookie: config.cookie,
        },
      },
      (err) => {
        if (err) {
          console.error("Error initializing i18n client", err);
        }
      },
    );

  if (iteration >= MAX_ITERATIONS) {
    console.debug(`Max iterations reached: ${MAX_ITERATIONS}`);

    client = i18n;
    return client;
  }

  if (loadedLanguages.size === 0 || loadedNamespaces.size === 0) {
    iteration++;

    console.debug(
      `Keeping component from rendering if no languages or namespaces are loaded. Iteration: ${iteration}. Will stop after ${MAX_ITERATIONS} iterations.`,
    );

    throw new Error("No languages or namespaces loaded");
  }

  client = i18n;
  return client;
};

/**
 * Build an instance synchronously from resources the server already loaded, so the first render
 * (including the server render) has real translations instead of nothing.
 */
const createI18nFromResources = ({
  locale,
  defaultLocale,
  ns,
  resources,
}: {
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
  resources: Resource;
}) => {
  const instance = i18next.createInstance();
  void instance
    .use(initReactI18next)
    .use(
      resourcesToBackend(
        (
          language: (typeof config.locales)[number],
          namespace: (typeof config.namespaces)[number],
        ) => loadTranslation(language, namespace),
      ),
    )
    .init({
      ...getInitOptions({ locale, defaultLocale, ns }),
      lng: isLocaleSupported(locale) ? locale : config.defaultLocale,
      resources,
      // Other languages still load on demand through the backend.
      partialBundledLanguages: true,
      initAsync: false,
    });
  return instance;
};

export const useTranslation = <
  Ns extends FlatNamespace | FlatNamespace[] | undefined = undefined,
  KPrefix extends KeyPrefix<FallbackNs<Ns>> = undefined,
>(
  ns?: Ns,
  options?: UseTranslationOptions<KPrefix>,
) => useTranslationBase<Ns, KPrefix>(ns, options);

export const getI18n = async ({
  locale,
  defaultLocale,
  ns,
}: {
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
}) => {
  if (!client) {
    return initializeI18nClient({ locale, defaultLocale, ns });
  }

  const nextLocale = isLocaleSupported(locale) ? locale : config.defaultLocale;

  await client.changeLanguage(nextLocale);
  dayjs.locale(nextLocale);
  const t = client.getFixedT<Namespace>(client.language, ns);
  z.config({
    localeError: makeZodI18nMap({ t: t as TFunction }),
  });

  if (ns) {
    await client.loadNamespaces(ns);
  }
  return client;
};

export const I18nProvider = ({
  children,
  locale,
  defaultLocale,
  ns,
  resources,
}: {
  children: React.ReactNode;
  locale?: string;
  defaultLocale?: string;
  ns?: Namespace;
  /** Preloaded translations from the server. Without them, children render only after loading. */
  resources?: Resource;
}) => {
  const [i18nClient, setI18nClient] = useState<i18n | null>(() => {
    if (client) return client;
    if (!resources) return null;
    const instance = createI18nFromResources({
      locale,
      defaultLocale,
      ns,
      resources,
    });
    // Module state is shared across requests on the server, so only cache it in the browser.
    if ("window" in globalThis) client = instance;
    return instance;
  });
  const nextLocale = isLocaleSupported(locale) ? locale : config.defaultLocale;

  useEffect(() => {
    void (async () => {
      if (!client) {
        setI18nClient(await getI18n({ locale, defaultLocale, ns }));
      }
    })();
  }, [client]);

  useEffect(() => {
    if (i18nClient) {
      void i18nClient.changeLanguage(nextLocale);
    }
  }, [nextLocale, i18nClient]);

  if (!i18nClient) {
    return null;
  }

  const t = i18nClient.getFixedT<Namespace>(i18nClient.language, ns);

  z.config({
    localeError: makeZodI18nMap({ t: t as TFunction }),
  });

  dayjs.locale(nextLocale);

  return <I18nextProvider i18n={i18nClient}>{children}</I18nextProvider>;
};

export type { ParseKeys as TranslationKey, Resource } from "i18next";
