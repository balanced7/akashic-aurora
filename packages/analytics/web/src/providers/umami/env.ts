/* eslint-disable turbo/no-undeclared-env-vars */
import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const preset = {
  id: "umami",
  client: {
    NEXT_PUBLIC_UMAMI_HOST: z.string(),
    NEXT_PUBLIC_UMAMI_WEBSITE_ID: z.string(),
  },
  server: {
    UMAMI_API_HOST: z.string(),
    UMAMI_API_KEY: z.string().optional(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
  env: {
    ...process.env,
    NEXT_PUBLIC_UMAMI_HOST: process.env.NEXT_PUBLIC_UMAMI_HOST,
    NEXT_PUBLIC_UMAMI_WEBSITE_ID: process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID,
  },
});
