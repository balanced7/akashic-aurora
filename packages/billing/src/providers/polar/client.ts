import { Polar } from "@polar-sh/sdk";

import { NodeEnv } from "@akashic-labs/shared/constants";

import { env } from "./env";

let polarInstance: Polar | null = null;

export const polar = () => {
  polarInstance ??= new Polar({
    server: env.NODE_ENV === NodeEnv.PRODUCTION ? "production" : "sandbox",
    accessToken: env.POLAR_ACCESS_TOKEN,
  });

  return polarInstance;
};
