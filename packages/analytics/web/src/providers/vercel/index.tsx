import { track } from "@vercel/analytics";
import { Analytics } from "@vercel/analytics/react";

import type { AnalyticsProviderClientStrategy } from "../types";

const Provider: AnalyticsProviderClientStrategy["Provider"] = ({
  children,
}) => {
  return (
    <>
      {children}
      <Analytics />
    </>
  );
};

export { Provider, track };
