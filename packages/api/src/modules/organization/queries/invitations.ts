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
import { invitation } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { GetInvitationsInput } from "../../../schema";

export const getInvitations = async ({
  organizationId,
  ...input
}: GetInvitationsInput & { organizationId: string }) => {
  const offset = (input.page - 1) * input.perPage;

  const where = and(
    input.email ? ilike(invitation.email, `%${input.email}%`) : undefined,
    input.role ? inArray(invitation.role, input.role) : undefined,
    input.status ? inArray(invitation.status, input.status) : undefined,
    input.expiresAt
      ? between(
          invitation.expiresAt,
          dayjs(input.expiresAt[0]).startOf("day").toDate(),
          dayjs(input.expiresAt[1]).endOf("day").toDate(),
        )
      : undefined,
    eq(invitation.organizationId, organizationId),
  );

  const orderBy = input.sort
    ? getOrderByFromSort({ sort: input.sort, defaultSchema: invitation })
    : [asc(invitation.email)];

  return db.transaction(async (tx) => {
    const data = await db
      .select()
      .from(invitation)
      .where(where)
      .limit(input.perPage)
      .offset(offset)
      .orderBy(...orderBy);

    const total = await tx
      .select({
        count: count(),
      })
      .from(invitation)
      .where(where)
      .execute()
      .then((res) => res[0]?.count ?? 0);

    return {
      data,
      total,
    };
  });
};
