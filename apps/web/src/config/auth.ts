import env from "env.config";

import { SocialProvider, authConfigSchema } from "@akashic-labs/auth";

import type { AuthConfig } from "@akashic-labs/auth";

export const authConfig = authConfigSchema.parse({
  providers: {
    password: env.NEXT_PUBLIC_AUTH_PASSWORD,
    magicLink: env.NEXT_PUBLIC_AUTH_MAGIC_LINK,
    passkey: env.NEXT_PUBLIC_AUTH_PASSKEY,
    anonymous: env.NEXT_PUBLIC_AUTH_ANONYMOUS,
    oAuth: [SocialProvider.APPLE, SocialProvider.GOOGLE, SocialProvider.GITHUB],
  },
}) satisfies AuthConfig;
