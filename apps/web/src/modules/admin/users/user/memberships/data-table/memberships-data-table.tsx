"use client";

import { pickBy } from "@akashic-labs/shared/utils";
import { DataTable } from "@akashic-labs/ui-web/data-table/data-table";
import { DataTableSkeleton } from "@akashic-labs/ui-web/data-table/data-table-skeleton";
import { DataTableToolbar } from "@akashic-labs/ui-web/data-table/data-table-toolbar";

import { admin } from "~/modules/admin/lib/api";
import { useDataTable } from "~/modules/common/hooks/use-data-table";

import { useColumns } from "./columns";

interface MembershipsDataTableProps {
  readonly userId: string;
}

export const MembershipsDataTable = ({ userId }: MembershipsDataTableProps) => {
  const columns = useColumns();

  const { table, query } = useDataTable({
    persistance: "local",
    columns,
    initialState: {
      sorting: [
        {
          id: "organization.name",
          desc: false,
        },
      ],
    },
    enableRowSelection: false,
    query: ({ page, perPage, sorting, filters }) =>
      admin.queries.users.getMemberships({
        id: userId,
        page: page.toString(),
        perPage: perPage.toString(),
        sort: JSON.stringify(sorting),
        ...pickBy(filters, Boolean),
      }),
  });

  if (query.isLoading) {
    return (
      <DataTableSkeleton
        columnCount={4}
        filterCount={3}
        cellWidths={["20rem", "10rem", "7rem", "4rem"]}
        shrinkZero
      />
    );
  }

  return (
    <div className="flex w-full flex-col gap-2">
      <DataTableToolbar table={table} />
      <DataTable table={table} />
    </div>
  );
};
