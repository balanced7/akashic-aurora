import {
  createSearchParamsCache,
  parseAsArrayOf,
  parseAsInteger,
  parseAsString,
} from "nuqs/server";
import { Suspense } from "react";

import { getOrganizationsResponseSchema } from "@akashic-labs/api/schema";
import { handle } from "@akashic-labs/api/utils";
import { getTranslation } from "@akashic-labs/i18n/server";
import { pickBy } from "@akashic-labs/shared/utils";
import { DataTableSkeleton } from "@akashic-labs/ui-web/data-table/data-table-skeleton";

import { api } from "~/lib/api/server";
import { getMetadata } from "~/lib/metadata";
import { OrganizationsDataTable } from "~/modules/admin/organizations/data-table/organizations-data-table";
import { getSortingStateParser } from "~/modules/common/hooks/use-data-table/common";
import {
  DashboardHeader,
  DashboardHeaderDescription,
  DashboardHeaderTitle,
} from "~/modules/common/layout/dashboard/header";

export const generateMetadata = getMetadata({
  title: "admin:organizations.header.title",
  description: "admin:organizations.header.description",
});

const searchParamsCache = createSearchParamsCache({
  page: parseAsInteger.withDefault(1),
  perPage: parseAsInteger.withDefault(10),
  sort: getSortingStateParser().withDefault([{ id: "name", desc: false }]),
  q: parseAsString,
  createdAt: parseAsArrayOf(parseAsInteger),
  members: parseAsArrayOf(parseAsInteger),
});

export default async function OrganizationsPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const searchParams = await props.searchParams;
  const { page, perPage, sort, ...rest } =
    searchParamsCache.parse(searchParams);
  const { t } = await getTranslation({ ns: "admin" });

  const filters = pickBy(rest, Boolean);

  const promise = handle(api.admin.organizations.$get, {
    schema: getOrganizationsResponseSchema,
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
            {t("organizations.header.title")}
          </DashboardHeaderTitle>
          <DashboardHeaderDescription>
            {t("organizations.header.description")}
          </DashboardHeaderDescription>
        </div>
      </DashboardHeader>
      <Suspense
        fallback={
          <DataTableSkeleton
            columnCount={3}
            filterCount={3}
            cellWidths={["15rem", "10rem", "10rem"]}
            shrinkZero
          />
        }
      >
        <OrganizationsDataTable promise={promise} perPage={perPage} />
      </Suspense>
    </>
  );
}
