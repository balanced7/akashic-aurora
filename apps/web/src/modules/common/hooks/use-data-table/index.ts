/* eslint-disable react-hooks/rules-of-hooks */
import { useLocalDataTable } from "./local";
import { useSearchParamsDataTable } from "./search-params";

import type { UseLocalDataTableProps } from "./local";
import type { UseSearchParamsDataTableProps } from "./search-params";
import type { useQuery } from "@tanstack/react-query";
import type { UseQueryOptions } from "@tanstack/react-query";
import type { useReactTable } from "@tanstack/react-table";

export function useDataTable<
  TData,
  TQueryFnData extends { data?: TData[]; total?: number },
  TQuery extends UseQueryOptions<TQueryFnData>,
>(
  props: UseLocalDataTableProps<TData, TQueryFnData, TQuery>,
): {
  table: ReturnType<typeof useReactTable<TData>>;
  query: ReturnType<typeof useQuery<TQueryFnData>>;
};
export function useDataTable<TData>(
  props: UseSearchParamsDataTableProps<TData>,
): { table: ReturnType<typeof useReactTable<TData>> };

export function useDataTable<
  TData,
  TQueryFnData extends { data?: TData[]; total?: number },
  TQuery extends UseQueryOptions<TQueryFnData>,
>(
  props:
    | UseLocalDataTableProps<TData, TQueryFnData, TQuery>
    | UseSearchParamsDataTableProps<TData>,
) {
  if (props.persistance === "local") {
    return useLocalDataTable(props);
  }
  return useSearchParamsDataTable(props);
}
