import dayjs from "dayjs";

import {
  and,
  asc,
  between,
  count,
  eq,
  getOrderByFromSort,
  ilike,
  inArray,
} from "@akashic-labs/db";
import { customer, user } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { GetCustomersInput } from "../../../schema";

export const getCustomersCount = async () =>
  db
    .select({ count: count() })
    .from(customer)
    .then((res) => res[0]?.count ?? 0);

export const getCustomers = async (input: GetCustomersInput) => {
  const offset = (input.page - 1) * input.perPage;

  const where = and(
    input.q ? ilike(user.name, `%${input.q}%`) : undefined,
    input.status ? inArray(customer.status, input.status) : undefined,
    input.plan ? inArray(customer.plan, input.plan) : undefined,
    input.createdAt
      ? between(
          customer.createdAt,
          dayjs(input.createdAt[0]).startOf("day").toDate(),
          dayjs(input.createdAt[1]).endOf("day").toDate(),
        )
      : undefined,
  );

  const orderBy = input.sort
    ? getOrderByFromSort({ sort: input.sort, defaultSchema: customer })
    : [asc(user.name)];

  return db.transaction(async (tx) => {
    const data = await db
      .select({
        id: customer.id,
        customerId: customer.customerId,
        userId: customer.userId,
        plan: customer.plan,
        status: customer.status,
        createdAt: customer.createdAt,
        updatedAt: customer.updatedAt,
        user: {
          name: user.name,
          image: user.image,
        },
      })
      .from(customer)
      .leftJoin(user, eq(customer.userId, user.id))
      .where(where)
      .limit(input.perPage)
      .offset(offset)
      .orderBy(...orderBy);

    const total = await tx
      .select({ count: count() })
      .from(customer)
      .leftJoin(user, eq(customer.userId, user.id))
      .where(where)
      .execute()
      .then((res) => res[0]?.count ?? 0);

    return {
      data,
      total,
    };
  });
};
