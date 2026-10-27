import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import { sharedPreset } from "../../utils/env";

import type { Preset } from "envin/types";

export const preset = {
  id: "nodemailer",
  server: {
    NODEMAILER_HOST: z.string(),
    NODEMAILER_PORT: z.coerce.number(),
    NODEMAILER_USER: z.string(),
    NODEMAILER_PASSWORD: z.string(),
  },
  extends: [sharedPreset],
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
});
