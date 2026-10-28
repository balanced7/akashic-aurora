"use client";

import { Provider } from "@akashic-labs/analytics-web";

export const AnalyticsProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  return <Provider>{children}</Provider>;
};
