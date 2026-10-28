import {
  parseAsArrayOf,
  parseAsInteger,
  parseAsString,
  parseAsStringEnum,
} from "nuqs/server";
import { createSearchParamsCache } from "nuqs/server";
import { Suspense } from "react";

import { getCustomersResponseSchema } from "@akashic-labs/api/schema";
import { handle } from "@akashic-labs/api/utils";
import { BillingStatus, PricingPlanType } from "@akashic-labs/billing";
import { getTranslation } from "@akashic-labs/i18n/server";
import { pickBy } from "@akashic-labs/shared/utils";
import { DataTableSkeleton } from "@akashic-labs/ui-web/data-table/data-table-skeleton";

import { api } from "~/lib/api/server";
import { getMetadata } from "~/lib/metadata";
import { CustomersDataTable } from "~/modules/admin/customers/data-table/customers-data-table";
import { getSortingStateParser } from "~/modules/common/hooks/use-data-table/common";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";

export const generateMetadata = getMetadata({
  title: "admin:customers.header.title",
  description: "admin:customers.header.description",
});

const searchParamsCache = createSearchParamsCache({
  page: parseAsInteger.withDefault(1),
  perPage: parseAsInteger.withDefault(10),
  sort: getSortingStateParser().withDefault([{ id: "user.name", desc: false }]),
  q: parseAsString,
  status: parseAsArrayOf(
    parseAsStringEnum<BillingStatus>(Object.values(BillingStatus)),
  ),
  plan: parseAsArrayOf(
    parseAsStringEnum<PricingPlanType>(Object.values(PricingPlanType)),
  ),
  createdAt: parseAsArrayOf(parseAsInteger),
});

export default async function CustomersPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { t } = await getTranslation({ ns: "admin" });
  const searchParams = await props.searchParams;
  const { page, perPage, sort, ...rest } =
    searchParamsCache.parse(searchParams);

  const filters = pickBy(rest, Boolean);

  const promise = handle(api.admin.customers.$get, {
    schema: getCustomersResponseSchema,
  })({
    query: {
      ...filters,
      page: page.toString(),
      perPage: perPage.toString(),
      sort: JSON.stringify(sort),
    },
  });

  return (
    <>
      <DashboardHeader>
        <div>
          <DashboardHeaderTitle>
            {t("customers.header.title")}
          </DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("customers.header.description")}
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>

      <Suspense
        fallback={
          <DataTableSkeleton
            columnCount={3}
            filterCount={4}
            cellWidths={["15rem", "10rem", "10rem"]}
            shrinkZero
          />
        }
      >
        <CustomersDataTable promise={promise} perPage={perPage} />
      </Suspense>
    </>
  );
}
