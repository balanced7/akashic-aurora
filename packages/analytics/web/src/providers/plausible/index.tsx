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
        defer
        data-domain={env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN}
        src={`${env.NEXT_PUBLIC_PLAUSIBLE_HOST}/js/script.js`}
      />
    </>
  );
};

const track: AnalyticsProviderClientStrategy["track"] = (event, data) => {
  if (typeof window === "undefined" || !(window as any).plausible) {
    return;
  }

  (window as any).plausible(event, {
    props: data,
  });
};

export { Provider, track };
