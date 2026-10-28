import { OpenPanel } from "@openpanel/nextjs";

import { env } from "./env";

import type { AnalyticsProviderServerStrategy } from "../types";

let client: OpenPanel | null = null;

const getClient = () => {
  if (client) {
    return client;
  }

  client = new OpenPanel({
    clientId: env.NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID,
    clientSecret: env.OPEN_PANEL_SECRET,
  });

  return client;
};

const track: AnalyticsProviderServerStrategy["track"] = (event, data) => {
  const client = getClient();

  void client.track(event, data);
};

export { track };
