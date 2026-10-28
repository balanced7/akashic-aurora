/* eslint-disable turbo/no-undeclared-env-vars */
import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const preset = {
  id: "open-panel",
  client: {
    NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID: z.string(),
  },
  server: {
    OPEN_PANEL_SECRET: z.string(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
  env: {
    ...process.env,
    NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID:
      process.env.NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID,
  },
});
