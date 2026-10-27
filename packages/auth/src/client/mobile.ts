import { expoClient } from "@better-auth/expo/client";
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

import type { AuthMobileClientOptions } from "..";
import type { auth } from "../server";
import type { AuthClientOptions } from "../types";

export const createClient = ({
  mobile,
  ...options
}: AuthClientOptions & { mobile: AuthMobileClientOptions }) =>
  createAuthClient({
    ...options,
    plugins: [
      ...(options.plugins ?? []),
      passkeyClient(),
      anonymousClient(),
      magicLinkClient(),
      lastLoginMethodClient(),
      twoFactorClient(),
      adminClient(),
      organizationClient(),
      inferAdditionalFields<typeof auth>(),
      expoClient(mobile),
    ],
  });
