import { asc, desc } from "drizzle-orm";

import * as schema from "../schema";

import type { SortPayload } from "@akashic-labs/shared/schema";
import type { PgTableWithColumns, TableConfig } from "drizzle-orm/pg-core";

export const getOrderByFromSort = <Schema extends TableConfig>({
  sort,
  defaultSchema,
}: {
  sort: SortPayload[];
  defaultSchema: PgTableWithColumns<Schema>;
}) => {
  return sort.map((s) => {
    const order = s.desc ? desc : asc;
    const parts = s.id.split(/[_.]/);

    const table =
      parts[0] && parts[0] in schema
        ? schema[parts[0] as keyof typeof schema]
        : defaultSchema;
    return order(table[(parts[1] ?? parts[0]) as keyof typeof table]);
  });
};
