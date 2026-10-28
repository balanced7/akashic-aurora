"use client";

import { use } from "react";

import { DataTable } from "@akashic-labs/ui-web/data-table/data-table";
import { DataTableToolbar } from "@akashic-labs/ui-web/data-table/data-table-toolbar";

import { useDataTable } from "~/modules/common/hooks/use-data-table";

import { useColumns } from "./columns";

import type { GetCustomersResponse } from "@akashic-labs/api/schema";

interface CustomersDataTableProps {
  readonly promise: Promise<Awaited<GetCustomersResponse>>;
  readonly perPage: number;
}

export const CustomersDataTable = ({
  promise,
  perPage,
}: CustomersDataTableProps) => {
  const columns = useColumns();
  const { data, total } = use(promise);

  const { table } = useDataTable({
    persistance: "searchParams",
    data,
    columns,
    pageCount: Math.ceil(total / perPage),
    initialState: {
      sorting: [
        {
          id: "user.name",
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
