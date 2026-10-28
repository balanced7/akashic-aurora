"use client";

import { use } from "react";

import { DataTable } from "@akashic-labs/ui-web/data-table/data-table";
import { DataTableToolbar } from "@akashic-labs/ui-web/data-table/data-table-toolbar";

import { useDataTable } from "~/modules/common/hooks/use-data-table";

import { useColumns } from "./columns";

import type { GetOrganizationsResponse } from "@akashic-labs/api/schema";

interface OrganizationsDataTableProps {
  readonly promise: Promise<GetOrganizationsResponse>;
  readonly perPage: number;
}

export const OrganizationsDataTable = ({
  promise,
  perPage,
}: OrganizationsDataTableProps) => {
  const { data, total, max } = use<GetOrganizationsResponse>(promise);
  const columns = useColumns({ max });

  const { table } = useDataTable({
    persistance: "searchParams",
    data,
    columns,
    pageCount: Math.ceil(total / perPage),
    initialState: {
      sorting: [
        {
          id: "name",
          desc: false,
        },
      ],
      columnVisibility: {
        q: false,
      },
    },
    shallow: false,
    clearOnDefault: true,
    enableRowSelection: false,
  });

  return (
    <div className="flex w-full flex-col gap-2">
      <DataTableToolbar table={table} />
      <DataTable table={table} />
    </div>
  );
};
