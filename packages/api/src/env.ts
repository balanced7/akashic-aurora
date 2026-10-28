import { defineEnv } from "envin";
import * as z from "zod";

import { preset as auth } from "@akashic-labs/auth/env";
import { preset as billing } from "@akashic-labs/billing/env";
import { preset as db } from "@akashic-labs/db/env";
import { preset as email } from "@akashic-labs/email/env";
import { envConfig } from "@akashic-labs/shared/constants";
import { preset as storage } from "@akashic-labs/storage/env";

import type { Preset } from "envin/types";

export const preset = {
  id: "api",
  server: {
    OPENAI_API_KEY: z.string().optional(), // change it to your provider API key (e.g. ANTHROPIC_API_KEY if you use Anthropic)
  },
  extends: [billing, auth, db, email, storage],
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
});
