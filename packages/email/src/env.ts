import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import { preset as providerPreset } from "./providers/env";

import type { Preset } from "envin/types";

export const preset = {
  id: "email",
  server: {
    PRODUCT_NAME: z.string().optional(),
  },
  extends: [providerPreset],
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
});
