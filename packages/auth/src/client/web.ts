import { passkeyClient } from "@better-auth/passkey/client";
import {
  magicLinkClient,
  twoFactorClient,
  anonymousClient,
  adminClient,
  organizationClient,
  inferAdditionalFields,
  lastLoginMethodClient,
} from "better-auth/client/plugins";
import { createAuthClient } from "better-auth/react";

import type { auth } from "../server";
import type { AuthClientOptions } from "../types";

export const createClient = (options?: AuthClientOptions) =>
  createAuthClient({
    ...options,
    plugins: [
      ...(options?.plugins ?? []),
      passkeyClient(),
      anonymousClient(),
      magicLinkClient(),
      twoFactorClient(),
      adminClient(),
      organizationClient(),
      lastLoginMethodClient(),
      inferAdditionalFields<typeof auth>(),
    ],
  });
