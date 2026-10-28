"use client";

import mixpanel from "mixpanel-browser";
import { useEffect } from "react";

import { NodeEnv } from "@akashic-labs/shared/constants";

import { env } from "./env";

import type { AnalyticsProviderClientStrategy } from "../types";

const init = () => {
  mixpanel.init(env.NEXT_PUBLIC_MIXPANEL_TOKEN, {
    debug: env.NODE_ENV === NodeEnv.DEVELOPMENT,
    autocapture: true,
    persistence: "localStorage",
  });
};

const Provider: AnalyticsProviderClientStrategy["Provider"] = ({
  children,
}) => {
  useEffect(() => {
    init();
  }, []);
  return children;
};

const track: AnalyticsProviderClientStrategy["track"] = (event, properties) => {
  if (typeof window === "undefined") {
    return;
  }

  mixpanel.track(event, properties);
};

export { Provider, track };
