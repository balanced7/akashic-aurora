/* eslint-disable turbo/no-undeclared-env-vars */
import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import { Locale } from "./types";

import type { Preset } from "envin/types";

export const preset = {
  id: "i18n",
  clientPrefix: "NEXT_PUBLIC_",
  client: {
    NEXT_PUBLIC_DEFAULT_LOCALE: z.string().optional().default(Locale.EN),
  },
  server: {
    DEFAULT_LOCALE: z.string().optional(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
  env: {
    DEFAULT_LOCALE: process.env.DEFAULT_LOCALE,
    NEXT_PUBLIC_DEFAULT_LOCALE: process.env.NEXT_PUBLIC_DEFAULT_LOCALE,
  },
});
