import { randomUUID } from "crypto";

import { env } from "./env";

import type {
  AllowedPropertyValues,
  AnalyticsProviderServerStrategy,
} from "../types";

const postEvent = async (
  event: string,
  data?: Record<string, AllowedPropertyValues>,
) => {
  const response = await fetch(
    `https://www.google-analytics.com/mp/collect?measurement_id=${env.NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID}&api_secret=${env.GOOGLE_ANALYTICS_SECRET}`,
    {
      method: "POST",
      body: JSON.stringify({
        client_id: data?.clientId ?? randomUUID(),
        events: [{ name: event, params: data }],
      }),
    },
  );

  if (!response.ok) {
    console.error("Failed to post event to Google Analytics: ", response);
  }
};

const track: AnalyticsProviderServerStrategy["track"] = (event, data) => {
  void postEvent(event, data);
};

export { track };
