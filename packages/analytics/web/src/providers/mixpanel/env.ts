/* eslint-disable turbo/no-undeclared-env-vars */
import { defineEnv } from "envin";
import * as z from "zod";

import { envConfig, NodeEnv } from "@akashic-labs/shared/constants";

import type { Preset } from "envin/types";

export const preset = {
  id: "mixpanel",
  client: {
    NEXT_PUBLIC_MIXPANEL_TOKEN: z.string(),
  },
} as const satisfies Preset;

export const env = defineEnv({
  ...envConfig,
  ...preset,
  shared: {
    NODE_ENV: z.enum(NodeEnv).default(NodeEnv.DEVELOPMENT),
  },
  env: {
    ...process.env,
    NEXT_PUBLIC_MIXPANEL_TOKEN: process.env.NEXT_PUBLIC_MIXPANEL_TOKEN,
  },
});
