import {
  getFacetedUniqueValues,
  getFacetedRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  getCoreRowModel,
  useReactTable,
  getFacetedMinMaxValues,
} from "@tanstack/react-table";
import {
  parseAsArrayOf,
  parseAsString,
  parseAsInteger,
  useQueryState,
  useQueryStates,
} from "nuqs";
import { useCallback, useMemo, useState } from "react";

import { useDebounceCallback } from "@akashic-labs/shared/hooks";

import {
  ARRAY_SEPARATOR,
  DEBOUNCE_MS,
  getFiltersFromColumnFilters,
  PAGE_KEY,
  PER_PAGE_KEY,
  SORT_KEY,
  THROTTLE_MS,
} from "./common";
import { getSortingStateParser } from "./common";

import type { CommonProps } from "./common";
import type {
  ColumnFiltersState,
  PaginationState,
  RowSelectionState,
  SortingState,
  Updater,
  VisibilityState,
} from "@tanstack/react-table";
import type { TableOptions } from "@tanstack/react-table";
import type { Parser, UseQueryStateOptions } from "nuqs";

export interface UseSearchParamsDataTableProps<TData>
  extends CommonProps, Omit<TableOptions<TData>, "state" | "getCoreRowModel"> {
  persistance: "searchParams";
  history?: "push" | "replace";
  throttleMs?: number;
  clearOnDefault?: boolean;
  enableAdvancedFilter?: boolean;
  scroll?: boolean;
  shallow?: boolean;
  startTransition?: React.TransitionStartFunction;
}

export function useSearchParamsDataTable<TData>(
  props: UseSearchParamsDataTableProps<TData>,
) {
  const {
    columns,
    initialState,
    history = "replace",
    debounceMs = DEBOUNCE_MS,
    throttleMs = THROTTLE_MS,
    clearOnDefault = false,
    scroll = false,
    shallow = true,
    startTransition,
    ...tableProps
  } = props;

  const queryStateOptions = useMemo<
    Omit<UseQueryStateOptions<string>, "parse">
  >(
    () => ({
      history,
      scroll,
      shallow,
      throttleMs,
      debounceMs,
      clearOnDefault,
      startTransition,
    }),
    [
      history,
      scroll,
      shallow,
      throttleMs,
      debounceMs,
      clearOnDefault,
      startTransition,
    ],
  );

  const [rowSelection, setRowSelection] = useState<RowSelectionState>(
    initialState?.rowSelection ?? {},
  );

  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
    initialState?.columnVisibility ?? {},
  );

  const [page, setPage] = useQueryState(
    PAGE_KEY,
    parseAsInteger.withOptions(queryStateOptions).withDefault(1),
  );
  const [perPage, setPerPage] = useQueryState(
    PER_PAGE_KEY,
    parseAsInteger
      .withOptions(queryStateOptions)
      .withDefault(initialState?.pagination?.pageSize ?? 10),
  );

  const pagination: PaginationState = useMemo(() => {
    return {
      pageIndex: page - 1,
      pageSize: perPage,
    };
  }, [page, perPage]);

  const onPaginationChange = useCallback(
    (updaterOrValue: Updater<PaginationState>) => {
      const newPagination =
        typeof updaterOrValue === "function"
          ? updaterOrValue(pagination)
          : updaterOrValue;
      void setPage(newPagination.pageIndex + 1);
      void setPerPage(newPagination.pageSize);
    },
    [pagination, setPage, setPerPage],
  );

  const columnIds = useMemo(() => {
    return new Set(columns.map((column) => column.id).filter(Boolean));
  }, [columns]);

  const [sorting, setSorting] = useQueryState(
    SORT_KEY,
    getSortingStateParser(columnIds)
      .withOptions(queryStateOptions)
      .withDefault(initialState?.sorting ?? []),
  );

  const onSortingChange = useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      void setSorting(
        typeof updaterOrValue === "function"
          ? updaterOrValue(sorting)
          : updaterOrValue,
      );
    },
    [sorting, setSorting],
  );

  const filterableColumns = useMemo(
    () => columns.filter((column) => column.enableColumnFilter),
    [columns],
  );

  const filterParsers = useMemo(() => {
    return filterableColumns.reduce<
      Record<string, Parser<string> | Parser<string[]>>
    >((acc, column) => {
      if (column.meta && "options" in column.meta && column.meta.options) {
        acc[column.id ?? ""] = parseAsArrayOf(
          parseAsString,
          ARRAY_SEPARATOR,
        ).withOptions(queryStateOptions);
      } else {
        acc[column.id ?? ""] = parseAsString.withOptions(queryStateOptions);
      }
      return acc;
    }, {});
  }, [filterableColumns, queryStateOptions]);

  const [filters, setFilters] = useQueryStates(filterParsers);

  const debouncedSetFilters = useDebounceCallback((values: typeof filters) => {
    void setPage(1);
    void setFilters(values);
  }, debounceMs);

  const initialColumnFilters: ColumnFiltersState = useMemo(() => {
    return Object.entries(filters).reduce<ColumnFiltersState>(
      (filters, [key, value]) => {
        if (value !== null) {
          const processedValue = Array.isArray(value)
            ? value
            : typeof value === "string" && /[^a-zA-Z0-9]/.test(value)
              ? value.split(/[^a-zA-Z0-9]+/).filter(Boolean)
              : [value];

          filters.push({
            id: key,
            value: processedValue,
          });
        }
        return filters;
      },
      [],
    );
  }, [filters]);

  const [columnFilters, setColumnFilters] =
    useState<ColumnFiltersState>(initialColumnFilters);

  const onColumnFiltersChange = useCallback(
    (updaterOrValue: Updater<ColumnFiltersState>) => {
      setColumnFilters((prev) => {
        const next =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev)
            : updaterOrValue;

        debouncedSetFilters(
          getFiltersFromColumnFilters({
            columnFilters: next,
            previousColumnFilters: prev,
            filterableColumns,
          }),
        );
        return next;
      });
    },
    [debouncedSetFilters, filterableColumns],
  );

  const table = useReactTable({
    columns,
    initialState,
    state: {
      pagination,
      sorting,
      columnVisibility,
      columnFilters,
      rowSelection,
    },
    enableRowSelection: true,
    onPaginationChange,
    onSortingChange,
    onColumnFiltersChange,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    getFacetedMinMaxValues: getFacetedMinMaxValues(),
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    ...tableProps,
  });

  return { table };
}
