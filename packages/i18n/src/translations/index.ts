import { en } from "./en";
import { nb } from "./nb";
import { sl } from "./sl";

import type { config } from "../config";

type NamespaceLoaders = Partial<
  Record<
    (typeof config.namespaces)[number],
    () => Promise<{ default: unknown }>
  >
>;

/**
 * `en` is the source of truth and carries every namespace. Other locales may
 * translate a subset of them - namespaces they don't provide fall back to `en`
 * through i18next's `fallbackLng`.
 */
export const translations = {
  en,
  sl,
  nb,
} as const satisfies Record<(typeof config.locales)[number], NamespaceLoaders>;
