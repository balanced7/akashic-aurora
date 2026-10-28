import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const preset = {
  id: "db",
  server: {
    DATABASE_URL: z.url(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
});
