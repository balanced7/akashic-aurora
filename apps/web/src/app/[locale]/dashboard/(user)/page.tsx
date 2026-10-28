import { getTranslation } from "@akashic-labs/i18n/server";

import { getMetadata } from "~/lib/metadata";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";
import { UserOrganizationInvitationsBanner } from "~/modules/organization/invitations/user/user-organization-invitations";
import { OrganizationPicker } from "~/modules/organization/organization-picker";

export const generateMetadata = getMetadata({
  title: "common:home",
  description: "dashboard:user.home.description",
});

export default async function UserPage() {
  const { t } = await getTranslation({ ns: "dashboard" });

  return (
    <>
      <UserOrganizationInvitationsBanner />
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>{t("user.home.title")}</DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("user.home.description")}
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>

      <OrganizationPicker />
    </>
  );
}
