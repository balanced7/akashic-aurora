import { eq } from "@akashic-labs/db";
import { customer } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { InsertCustomer } from "@akashic-labs/db/schema";

export const getCustomerByUserId = async (userId: string) => {
  const [data] = await db
    .select()
    .from(customer)
    .where(eq(customer.userId, userId));

  return data ?? null;
};

export const getCustomerByCustomerId = async (customerId: string) => {
  const [data] = await db
    .select()
    .from(customer)
    .where(eq(customer.customerId, customerId));

  return data ?? null;
};

export const updateCustomer = async (
  userId: string,
  data: Partial<InsertCustomer>,
) => {
  await db.update(customer).set(data).where(eq(customer.userId, userId));
};

export const upsertCustomer = async (data: InsertCustomer) => {
  await db.insert(customer).values(data).onConflictDoUpdate({
    target: customer.userId,
    set: data,
  });
};
