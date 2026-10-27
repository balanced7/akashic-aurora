import { eq } from "@akashic-labs/db";
import { customer } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { UpdateCustomer } from "@akashic-labs/db/schema";

export const deleteCustomer = async ({ id }: { id: string }) =>
  db.delete(customer).where(eq(customer.id, id));

export const updateCustomer = async ({
  id,
  data,
}: {
  id: string;
  data: UpdateCustomer;
}) => db.update(customer).set(data).where(eq(customer.id, id));
