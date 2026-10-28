import { OpenPanelComponent, useOpenPanel } from "@openpanel/nextjs";

import { env } from "./env";

import type { AnalyticsProviderClientStrategy } from "../types";

const Provider: AnalyticsProviderClientStrategy["Provider"] = ({
  children,
}) => {
  return (
    <>
      {children}
      <OpenPanelComponent
        clientId={env.NEXT_PUBLIC_OPEN_PANEL_CLIENT_ID}
        trackScreenViews
        trackAttributes
        trackOutgoingLinks
      />
    </>
  );
};

const track: AnalyticsProviderClientStrategy["track"] = (event, data) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  useOpenPanel().track(event, data);
};

export { Provider, track };
