/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
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
        src={`${env.NEXT_PUBLIC_UMAMI_HOST}/script.js`}
        data-website-id={env.NEXT_PUBLIC_UMAMI_WEBSITE_ID}
      ></script>
    </>
  );
};

const track: AnalyticsProviderClientStrategy["track"] = (event, data) => {
  if (typeof window === "undefined" || !(window as any).umami) {
    return;
  }

  (window as any).umami.track(event, {
    props: data,
  });
};

export { Provider, track };
