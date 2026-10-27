import { describe, expect, it } from "vitest";

import { config } from "../config";

import { translations } from ".";

const nonDefaultLocales = config.locales.filter((locale) => locale !== "en");

const flatten = (value: object, prefix = ""): string[] =>
  Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;

    return typeof child === "object" && child !== null
      ? flatten(child as object, path)
      : [path];
  });

// Plural suffixes vary per language (Slovene has four, Norwegian two), so keys
// are compared on their singular base.
const baseKeys = (value: object) =>
  new Set(
    flatten(value).map((key) => key.replace(/_(one|two|few|many|other)$/, "")),
  );

describe.each(nonDefaultLocales)("%s translations", (locale) => {
  it.each(config.namespaces)(
    "cover every key of the en %s namespace",
    async (namespace) => {
      const { default: source } = await translations.en[namespace]();
      const { default: translated } = await translations[locale][namespace]();

      expect(baseKeys(translated as object)).toEqual(
        baseKeys(source as object),
      );
    },
  );
});
