import { env } from "./env";

import type { AnalyticsProviderServerStrategy } from "../types";

const track: AnalyticsProviderServerStrategy["track"] = (event, data) => {
  const url = typeof data?.url === "string" ? data.url : "app://server-side";
  const referrer =
    typeof data?.referrer === "string" ? data.referrer : undefined;
  const ip = typeof data?.ip === "string" ? data.ip : undefined;

  const props = data
    ? Object.fromEntries(
        Object.entries(data).filter(
          ([key]) => !["url", "referrer", "ip"].includes(key),
        ),
      )
    : undefined;

  void fetch(`${env.NEXT_PUBLIC_PLAUSIBLE_HOST}/api/event`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "AkashicLabs-Server/1.0 (Server-side tracking)",
      ...(ip && { "X-Forwarded-For": ip }),
    },
    body: JSON.stringify({
      domain: env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN,
      name: event,
      url: url,
      ...(referrer && { referrer }),
      ...(props && Object.keys(props).length > 0 && { props }),
    }),
  }).then((res) => {
    if (!res.ok) {
      console.error("Failed to post event to Plausible: ", res);
    }
  });
};

export { track };
