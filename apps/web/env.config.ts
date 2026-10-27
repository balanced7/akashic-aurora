import { defineEnv } from "envin";
import { vercel } from "envin/presets/zod";
import * as z from "zod";

import { preset as analytics } from "@akashic-labs/analytics-web/env";
import { preset as api } from "@akashic-labs/api/env";
import { preset as i18n } from "@akashic-labs/i18n/env";
import { envConfig, NodeEnv } from "@akashic-labs/shared/constants";
import { ThemeColor, ThemeMode } from "@akashic-labs/ui";

const castStringToBool = z.preprocess((val) => {
  if (typeof val === "string") {
    if (["1", "true"].includes(val.toLowerCase())) return true;
    if (["0", "false"].includes(val.toLowerCase())) return false;
  }
  return val;
}, z.coerce.boolean());

export default defineEnv({
  ...envConfig,
  extends: [vercel, api, analytics, i18n],
  shared: {
    NODE_ENV: z.enum(NodeEnv).default(NodeEnv.DEVELOPMENT),
    ANALYZE: castStringToBool.optional().default(false),
  },
  /**
   * Specify your server-side environment variables schema here.
   * This way you can ensure the app isn't built with invalid env vars.
   */
  server: {
    CONTACT_EMAIL: z.email(),
  },

  /**
   * Specify your client-side environment variables schema here.
   * For them to be exposed to the client, prefix them with `NEXT_PUBLIC_`.
   */
  clientPrefix: "NEXT_PUBLIC_",
  client: {
    NEXT_PUBLIC_AUTH_PASSWORD: castStringToBool.optional().default(true),
    NEXT_PUBLIC_AUTH_MAGIC_LINK: castStringToBool.optional().default(false),
    NEXT_PUBLIC_AUTH_PASSKEY: castStringToBool.optional().default(true),
    NEXT_PUBLIC_AUTH_ANONYMOUS: castStringToBool.optional().default(true),

    NEXT_PUBLIC_PRODUCT_NAME: z.string(),
    NEXT_PUBLIC_URL: z.url(),
    NEXT_PUBLIC_DEFAULT_LOCALE: z.string().optional().default("en"),
    NEXT_PUBLIC_THEME_MODE: z
      .enum(ThemeMode)
      .optional()
      .default(ThemeMode.SYSTEM),
    NEXT_PUBLIC_THEME_COLOR: z
      .enum(ThemeColor)
      .optional()
      .default(ThemeColor.AKASHIC_LABS),
    /** Where the Aurora docs are hosted. Marketing pages link every doc topic under this base. */
    NEXT_PUBLIC_DOCS_URL: z
      .url()
      .optional()
      .default("https://docs.akashiclabs.dev"),
  },
  /**
   * Destructure all variables from `process.env` to make sure they aren't tree-shaken away.
   */
  env: {
    ...process.env,
    NEXT_PUBLIC_PRODUCT_NAME: process.env.NEXT_PUBLIC_PRODUCT_NAME,
    NEXT_PUBLIC_URL: process.env.NEXT_PUBLIC_URL,
    NEXT_PUBLIC_DEFAULT_LOCALE: process.env.NEXT_PUBLIC_DEFAULT_LOCALE,
    NEXT_PUBLIC_THEME_MODE: process.env.NEXT_PUBLIC_THEME_MODE,
    NEXT_PUBLIC_THEME_COLOR: process.env.NEXT_PUBLIC_THEME_COLOR,
    NEXT_PUBLIC_DOCS_URL: process.env.NEXT_PUBLIC_DOCS_URL,

    NEXT_PUBLIC_AUTH_PASSWORD: process.env.NEXT_PUBLIC_AUTH_PASSWORD,
    NEXT_PUBLIC_AUTH_MAGIC_LINK: process.env.NEXT_PUBLIC_AUTH_MAGIC_LINK,
    NEXT_PUBLIC_AUTH_PASSKEY: process.env.NEXT_PUBLIC_AUTH_PASSKEY,
    NEXT_PUBLIC_AUTH_ANONYMOUS: process.env.NEXT_PUBLIC_AUTH_ANONYMOUS,

    NEXT_PUBLIC_POSTHOG_KEY: process.env.NEXT_PUBLIC_POSTHOG_KEY,
    NEXT_PUBLIC_POSTHOG_HOST: process.env.NEXT_PUBLIC_POSTHOG_HOST,
    NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID:
      process.env.NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID,
    NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID:
      process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID,
    NEXT_PUBLIC_UMAMI_HOST: process.env.NEXT_PUBLIC_UMAMI_HOST,
    NEXT_PUBLIC_UMAMI_WEBSITE_ID: process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID,
    NEXT_PUBLIC_PLAUSIBLE_HOST: process.env.NEXT_PUBLIC_PLAUSIBLE_HOST,
    NEXT_PUBLIC_PLAUSIBLE_DOMAIN: process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN,
    NEXT_PUBLIC_MIXPANEL_TOKEN: process.env.NEXT_PUBLIC_MIXPANEL_TOKEN,
    NEXT_PUBLIC_VEMETRIC_PROJECT_TOKEN:
      process.env.NEXT_PUBLIC_VEMETRIC_PROJECT_TOKEN,
  },
});
