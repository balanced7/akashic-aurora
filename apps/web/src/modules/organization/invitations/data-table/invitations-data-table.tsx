"use client";

import { InvitationStatus } from "@akashic-labs/auth";
import { pickBy } from "@akashic-labs/shared/utils";
import { DataTable } from "@akashic-labs/ui-web/data-table/data-table";
import { DataTableSkeleton } from "@akashic-labs/ui-web/data-table/data-table-skeleton";
import { DataTableToolbar } from "@akashic-labs/ui-web/data-table/data-table-toolbar";

import { useDataTable } from "~/modules/common/hooks/use-data-table";
import { organization } from "~/modules/organization/lib/api";

import { useColumns } from "./columns";

interface InvitationsDataTableProps {
  readonly organizationId: string;
}

export const InvitationsDataTable = ({
  organizationId,
}: InvitationsDataTableProps) => {
  const columns = useColumns();

  const { table, query } = useDataTable({
    persistance: "local",
    columns,
    initialState: {
      sorting: [
        {
          id: "expiresAt",
          desc: true,
        },
      ],
      columnFilters: [
        {
          id: "status",
          value: [InvitationStatus.PENDING],
        },
      ],
    },
    enableRowSelection: false,
    query: ({ page, perPage, sorting, filters }) =>
      organization.queries.invitations.getAll({
        id: organizationId,
        page: page.toString(),
        perPage: perPage.toString(),
        sort: JSON.stringify(sorting),
        ...pickBy(filters, Boolean),
      }),
  });

  if (query.isLoading) {
    return (
      <DataTableSkeleton
        columnCount={5}
        filterCount={4}
        cellWidths={["20rem", "5rem", "5rem", "10rem", "2.5rem"]}
        shrinkZero
      />
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <DataTableToolbar table={table} />
      <DataTable table={table} />
    </div>
  );
};
