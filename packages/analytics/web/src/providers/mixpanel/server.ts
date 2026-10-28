import Mixpanel from "mixpanel";

import { NodeEnv } from "@akashic-labs/shared/constants";

import { env } from "./env";

import type { AnalyticsProviderServerStrategy } from "../types";

let client: Mixpanel.Mixpanel | null = null;

const getClient = () => {
  if (client) {
    return client;
  }

  client = Mixpanel.init(env.NEXT_PUBLIC_MIXPANEL_TOKEN, {
    debug: env.NODE_ENV === NodeEnv.DEVELOPMENT,
  });

  return client;
};

const track: AnalyticsProviderServerStrategy["track"] = (event, properties) => {
  try {
    const mixpanel = getClient();
    mixpanel.track(event, properties ?? {});
  } catch (error) {
    console.warn("Failed to track Mixpanel event: ", error);
  }
};

export { track };
