import { NuqsAdapter } from "nuqs/adapters/next/app";
import { memo } from "react";

import { I18nProvider } from "@akashic-labs/i18n";

import { appConfig } from "~/config/app";
import { QueryClientProvider } from "~/lib/query/client";

import { AnalyticsProvider } from "./analytics";
import { ThemeProvider } from "./theme";

import type { Resource } from "@akashic-labs/i18n";

interface ProvidersProps {
  readonly children: React.ReactNode;
  readonly locale: string;
  readonly resources?: Resource;
}

export const Providers = memo<ProvidersProps>(
  ({ children, locale, resources }) => {
    return (
      <I18nProvider
        locale={locale}
        defaultLocale={appConfig.locale}
        resources={resources}
      >
        <QueryClientProvider>
          <NuqsAdapter>
            <AnalyticsProvider>
              <ThemeProvider>{children}</ThemeProvider>
            </AnalyticsProvider>
          </NuqsAdapter>
        </QueryClientProvider>
      </I18nProvider>
    );
  },
);

Providers.displayName = "Providers";
