export const Locale = {
  EN: "en",
  SL: "sl",
  NB: "nb",
} as const;

export type Locale = (typeof Locale)[keyof typeof Locale];

export const LocaleLabel: Record<Locale, string> = {
  [Locale.EN]: "English",
  [Locale.SL]: "Slovenščina",
  [Locale.NB]: "Norsk",
} as const;

export type { TFunction } from "i18next";
