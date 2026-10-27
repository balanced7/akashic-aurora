/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-assignment */

import { env } from "./env";

import type { AnalyticsProviderClientStrategy } from "../types";

const Provider: AnalyticsProviderClientStrategy["Provider"] = ({
  children,
}) => {
  return (
    <>
      {children}
      <script
        async
        src={`https://www.googletagmanager.com/gtag/js?id=${env.NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID}`}
        onLoad={() => {
          if (typeof window === "undefined") {
            return;
          }

          (window as any).dataLayer = (window as any).dataLayer ?? [];

          function gtag(...rest: any[]) {
            (window as any).dataLayer.push(...rest);
          }

          (window as any).gtag = gtag;

          (window as any).gtag("js", new Date());
          (window as any).gtag(
            "config",
            env.NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID,
          );
        }}
      />
    </>
  );
};

const track: AnalyticsProviderClientStrategy["track"] = (event, data) => {
  if (typeof window === "undefined" || !(window as any).gtag) {
    return;
  }

  (window as any).gtag("event", event, data);
};

export { Provider, track };
