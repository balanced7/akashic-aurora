import Image from "next/image";

import { getTranslation } from "@akashic-labs/i18n/server";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@akashic-labs/ui-web/card";

import { getMetadata } from "~/lib/metadata";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";

export const generateMetadata = getMetadata({
  title: "repotrts",
  description: "marketing:reports.description",
});

export default async function Reports() {
  const { t } = await getTranslation({ ns: "reports" });
  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>{t("home.title")}</DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("home.description")}
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>

      <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="flex w-full flex-col justify-between">
          <CardHeader>
            <Image
              alt=""
              width={300}
              height={200}
              src="/images/features/reports/compatibility.png"
              className="h-48 w-full rounded-lg object-cover"
            />
          </CardHeader>
          <CardContent className="space-y-0.5">
            <CardTitle className="text-xl">
              {t("reports.compatibility.title")}
            </CardTitle>
            <CardDescription>
              {t("reports.compatibility.description")}
            </CardDescription>
          </CardContent>
          <CardFooter>
            <Button>{t("actions.take_report")}</Button>
          </CardFooter>
        </Card>
        <Card className="flex w-full flex-col justify-between">
          <CardHeader>
            <Image
              alt=""
              width={300}
              height={200}
              src="/images/features/reports/love_languages.png"
              className="h-48 w-full rounded-lg object-cover"
            />
          </CardHeader>
          <CardContent className="space-y-0.5">
            <CardTitle className="text-xl">
              {t("reports.love_languages.title")}
            </CardTitle>
            <CardDescription>
              {t("reports.love_languages.description")}
            </CardDescription>
          </CardContent>
          <CardFooter>
            <Button variant="secondary">{t("actions.view_results")}</Button>
          </CardFooter>
        </Card>
      </div>
    </>
  );
}
