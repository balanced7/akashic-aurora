import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const preset = {
  id: "s3",
  server: {
    S3_BUCKET: z.string().optional(),
    S3_REGION: z.string().optional().default("us-east-1"),
    S3_ENDPOINT: z.string(),
    S3_ACCESS_KEY_ID: z.string(),
    S3_SECRET_ACCESS_KEY: z.string(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
});
