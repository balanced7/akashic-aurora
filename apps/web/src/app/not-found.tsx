import { appConfig } from "~/config/app";
import { BaseLayout } from "~/modules/common/layout/base";
import { MarketingShell } from "~/modules/marketing/layout/marketing-shell";
import { NotFoundContent } from "~/modules/marketing/ui/not-found-content";

/** Unmatched URLs: a real 404 status, rendered inside the marketing site chrome. */
export default function NotFound() {
  return (
    <BaseLayout locale={appConfig.locale}>
      <MarketingShell locale={appConfig.locale}>
        <NotFoundContent />
      </MarketingShell>
    </BaseLayout>
  );
}
