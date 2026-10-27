"use client";

import dynamic from "next/dynamic";
import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";

import { env } from "./env";

import type { AnalyticsProviderClientStrategy } from "../types";

const PageView = dynamic(
  () => import("./page-view").then((mod) => mod.PageView),
  {
    ssr: false,
  },
);

// Template .env files ship "<your-posthog-api-key>"; skip init rather than send doomed requests.
const hasKey = env.NEXT_PUBLIC_POSTHOG_KEY.startsWith("phc_");

if (typeof window !== "undefined" && hasKey) {
  posthog.init(env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: env.NEXT_PUBLIC_POSTHOG_HOST,
    person_profiles: "always",
    capture_pageview: false,
    disable_external_dependency_loading: true,
    disable_session_recording: true,
  });
}

const Provider: AnalyticsProviderClientStrategy["Provider"] = ({
  children,
}) => {
  return (
    <PostHogProvider client={posthog}>
      {children}
      <PageView />
    </PostHogProvider>
  );
};

const track: AnalyticsProviderClientStrategy["track"] = (event, properties) => {
  if (typeof window === "undefined" || !hasKey) {
    return;
  }

  posthog.capture(event, properties);
};

export { Provider, track };
