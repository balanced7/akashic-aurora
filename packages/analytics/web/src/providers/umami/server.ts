import { env } from "./env";

import type { AnalyticsProviderServerStrategy } from "../types";

const track: AnalyticsProviderServerStrategy["track"] = (event, data) => {
  const hostname =
    typeof data?.hostname === "string" ? data.hostname : undefined;
  const language =
    typeof data?.language === "string" ? data.language : undefined;
  const referrer =
    typeof data?.referrer === "string" ? data.referrer : undefined;
  const screen = typeof data?.screen === "string" ? data.screen : undefined;
  const title = typeof data?.title === "string" ? data.title : undefined;
  const url = typeof data?.url === "string" ? data.url : "app://server-side";

  void fetch(`${env.UMAMI_API_HOST}/api/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-umami-api-key": env.UMAMI_API_KEY ?? "",
    },
    body: JSON.stringify({
      type: "event",
      payload: {
        website: env.NEXT_PUBLIC_UMAMI_WEBSITE_ID,
        name: event,
        url: url,
        ...(hostname && { hostname }),
        ...(language && { language }),
        ...(referrer && { referrer }),
        ...(screen && { screen }),
        ...(title && { title }),
        data,
      },
    }),
  }).then((res) => {
    if (!res.ok) {
      console.error("Failed to post event to Umami: ", res);
    }
  });
};

export { track };
