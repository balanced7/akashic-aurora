import { redirect } from "next/navigation";

import { pathsConfig } from "~/config/paths";
import { getSession } from "~/lib/auth/server";
import { getMetadata } from "~/lib/metadata";
import { ManagePlan } from "~/modules/user/settings/billing/manage-plan";
import { PlanSummary } from "~/modules/user/settings/billing/plan-summary";

export const generateMetadata = getMetadata({
  title: "billing",
  description: "billing:manage.description",
});

export default async function BillingPage() {
  const { user } = await getSession();

  if (!user) {
    return redirect(pathsConfig.auth.login);
  }

  return (
    <>
      <PlanSummary />
      <ManagePlan />
    </>
  );
}
