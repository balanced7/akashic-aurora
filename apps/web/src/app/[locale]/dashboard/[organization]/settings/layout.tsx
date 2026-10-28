import { getTranslation } from "@akashic-labs/i18n/server";

import { pathsConfig } from "~/config/paths";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";
import { SettingsNav } from "~/modules/user/settings/layout/nav";

const LINKS = (organization: string) =>
  [
    {
      label: "general",
      href: pathsConfig.dashboard.organization(organization).settings.index,
    },
  ] as const;

export default async function SettingsLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{
    organization: string;
  }>;
}) {
  const { t } = await getTranslation({ ns: ["common", "organization"] });

  const organization = (await params).organization;

  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>
            {t("settings.header.title")}
          </DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("settings.header.description")}
          </DashboardHeaderDescription>
        </div>

        <div className="lg:hidden">
          <SettingsNav
            links={LINKS(organization).map((link) => ({
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
              links={LINKS(organization).map((link) => ({
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
