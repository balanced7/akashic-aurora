import { getTranslation } from "@akashic-labs/i18n/server";

import { pathsConfig } from "~/config/paths";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";
import { SettingsNav } from "~/modules/user/settings/layout/nav";

const LINKS = [
  {
    label: "general",
    href: pathsConfig.dashboard.user.settings.index,
  },
  {
    label: "security",
    href: pathsConfig.dashboard.user.settings.security,
  },
  {
    label: "billing",
    href: pathsConfig.dashboard.user.settings.billing,
  },
] as const;

export default async function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { t } = await getTranslation({ ns: ["common", "auth"] });

  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>
            {t("account.settings.header.title")}
          </DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("account.settings.header.description")}
          </DashboardHeaderDescription>
        </div>

        <div className="lg:hidden">
          <SettingsNav
            links={LINKS.map((link) => ({
              ...link,
              label: t(link.label),
            }))}
          />
        </div>
      </DashboardHeader>
      <div className="flex w-full gap-3">
        <div className="hidden w-96 lg:block">
          <div className="sticky top-[calc(var(--banner-height)+theme(spacing.6))]">
            <SettingsNav
              links={LINKS.map((link) => ({
                ...link,
                label: t(link.label),
              }))}
            />
          </div>
        </div>
        <div className="flex w-full flex-col gap-6">{children}</div>
      </div>
    </>
  );
}
