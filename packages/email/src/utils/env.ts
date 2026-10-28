import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const sharedPreset = {
  id: "shared",
  server: {
    EMAIL_FROM: z.string(),
  },
} as const satisfies Preset;

export const sharedEnv = defineEnv({
  ...envConfig,
  ...sharedPreset,
});
