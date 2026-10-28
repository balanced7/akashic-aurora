import "i18next";

import type { config } from "../config";
import type { translations } from "../translations";

type ExtractDefault<T> = T extends () => Promise<infer R>
  ? R extends { default: infer D }
    ? D
    : never
  : never;

/** `en` carries every namespace, so it defines the shape of the resources. */
type Translation = (typeof translations)["en"];

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: typeof config.namespaces;
    resources: {
      [K in keyof Translation]: ExtractDefault<Translation[K]>;
    };
  }
}
