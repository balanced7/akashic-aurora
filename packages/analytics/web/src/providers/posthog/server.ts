import { PostHog } from "posthog-node";

import { env } from "./env";

import type { AnalyticsProviderServerStrategy } from "../types";

let client: PostHog | null = null;

const getClient = () => {
  if (client) {
    return client;
  }

  client = new PostHog(env.NEXT_PUBLIC_POSTHOG_KEY, {
    host: env.NEXT_PUBLIC_POSTHOG_HOST,
  });

  return client;
};

const track: AnalyticsProviderServerStrategy["track"] = (event, data) => {
  const client = getClient();

  client.capture({
    event,
    distinctId: typeof data?.distinctId === "string" ? data.distinctId : "",
    properties: data,
  });
};

export { track };
