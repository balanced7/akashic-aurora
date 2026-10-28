import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import { BillingModel } from "../types";

import type { Preset } from "envin/types";

export const sharedPreset = {
  id: "shared",
  server: {
    BILLING_MODEL: z
      .enum(BillingModel)
      .optional()
      .default(BillingModel.RECURRING),
  },
} as const satisfies Preset;

export const sharedEnv = defineEnv({
  ...envConfig,
  ...sharedPreset,
});
