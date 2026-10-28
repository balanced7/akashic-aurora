import { getTranslation } from "@akashic-labs/i18n/server";

import { getMetadata } from "~/lib/metadata";
import {
  DashboardHeader,
  DashboardHeaderTitle,
  DashboardHeaderDescription,
} from "~/modules/common/layout/dashboard/header";
import { AreaChart } from "~/modules/organization/home/charts/area";
import { BarChart } from "~/modules/organization/home/charts/bar";
import { LineChart } from "~/modules/organization/home/charts/line";
import { PieChart } from "~/modules/organization/home/charts/pie";
import { RadarChart } from "~/modules/organization/home/charts/radar";
import { RadialChart } from "~/modules/organization/home/charts/radial";
import { ShapeChart } from "~/modules/organization/home/charts/shape";

export const generateMetadata = getMetadata({
  title: "common:home",
  description: "dashboard:organization.home.description",
});

export default async function OrganizationPage() {
  const { t } = await getTranslation({ ns: "dashboard" });

  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>
            {t("organization.home.title")}
          </DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("organization.home.description")}
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>

      <div className="flex w-full flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <BarChart />
          <PieChart />
          <ShapeChart />
        </div>
        <AreaChart />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <RadialChart />
          <RadarChart />
        </div>
        <LineChart />
      </div>
    </>
  );
}
