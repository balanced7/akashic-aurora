import { createParser } from "nuqs/server";
import * as z from "zod";

import { sortSchema } from "@akashic-labs/shared/schema";

import type { ColumnDef, ColumnFiltersState } from "@tanstack/react-table";

const PAGE_KEY = "page";
const PER_PAGE_KEY = "perPage";
const SORT_KEY = "sort";
const ARRAY_SEPARATOR = ",";
const DEBOUNCE_MS = 500;
const THROTTLE_MS = 50;

interface CommonProps {
  debounceMs?: number;
}

const getFiltersFromColumnFilters = <TData>({
  columnFilters,
  previousColumnFilters,
  filterableColumns,
}: {
  columnFilters: ColumnFiltersState;
  previousColumnFilters?: ColumnFiltersState;
  filterableColumns: ColumnDef<TData>[];
}) => {
  const filterUpdates = columnFilters.reduce<
    Record<string, string | string[] | null>
  >((acc, filter) => {
    if (filterableColumns.find((column) => column.id === filter.id)) {
      acc[filter.id] = filter.value as string | string[];
    }
    return acc;
  }, {});

  for (const prevFilter of previousColumnFilters ?? []) {
    if (!columnFilters.some((filter) => filter.id === prevFilter.id)) {
      filterUpdates[prevFilter.id] = null;
    }
  }

  return filterUpdates;
};

const getSortingStateParser = (columnIds?: string[] | Set<string>) => {
  const validKeys = columnIds
    ? columnIds instanceof Set
      ? columnIds
      : new Set(columnIds)
    : null;

  return createParser({
    parse: (value) => {
      try {
        const parsed = JSON.parse(value);
        const result = z.array(sortSchema).safeParse(parsed);

        if (!result.success) return null;

        if (validKeys && result.data.some((item) => !validKeys.has(item.id))) {
          return null;
        }

        return result.data;
      } catch {
        return null;
      }
    },
    serialize: (value) => JSON.stringify(value),
    eq: (a, b) =>
      a.length === b.length &&
      a.every(
        (item, index) =>
          item.id === b[index]?.id && item.desc === b[index].desc,
      ),
  });
};

export {
  PAGE_KEY,
  PER_PAGE_KEY,
  SORT_KEY,
  ARRAY_SEPARATOR,
  DEBOUNCE_MS,
  THROTTLE_MS,
  getFiltersFromColumnFilters,
  getSortingStateParser,
  type CommonProps,
};
