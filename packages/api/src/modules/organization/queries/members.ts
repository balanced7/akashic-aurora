import dayjs from "dayjs";

import { MemberRole } from "@akashic-labs/auth";
import {
  and,
  asc,
  between,
  count,
  eq,
  getOrderByFromSort,
  ilike,
  inArray,
  or,
  sql,
} from "@akashic-labs/db";
import { member, user } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { GetMembersInput } from "../../../schema";

export const getMembers = async ({
  organizationId,
  ...input
}: GetMembersInput & { organizationId: string }) => {
  const offset = (input.page - 1) * input.perPage;

  const where = and(
    input.q
      ? or(ilike(user.name, `%${input.q}%`), ilike(user.email, `%${input.q}%`))
      : undefined,
    input.role ? inArray(member.role, input.role) : undefined,
    input.createdAt
      ? between(
          member.createdAt,
          dayjs(input.createdAt[0]).startOf("day").toDate(),
          dayjs(input.createdAt[1]).endOf("day").toDate(),
        )
      : undefined,
    eq(member.organizationId, organizationId),
  );

  const orderBy = input.sort
    ? getOrderByFromSort({ sort: input.sort, defaultSchema: member })
    : [asc(user.name)];

  return db.transaction(async (tx) => {
    const data = await tx
      .select({
        id: member.id,
        organizationId: member.organizationId,
        role: sql<MemberRole>`${member.role}`,
        createdAt: member.createdAt,
        userId: member.userId,
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
          image: user.image,
        },
      })
      .from(member)
      .leftJoin(user, eq(member.userId, user.id))
      .where(where)
      .limit(input.perPage)
      .offset(offset)
      .orderBy(...orderBy);

    const total = await tx
      .select({
        count: count(),
      })
      .from(member)
      .leftJoin(user, eq(member.userId, user.id))
      .where(where)
      .execute()
      .then((res) => res[0]?.count ?? 0);

    return {
      data,
      total,
    };
  });
};

export const getIsOnlyOwner = async ({
  organizationId,
  userId,
}: {
  organizationId: string;
  userId: string;
}) => {
  const otherOwners = await db.query.member.findMany({
    where: (member, { eq, and, not }) =>
      and(
        eq(member.organizationId, organizationId),
        eq(member.role, MemberRole.OWNER),
        not(eq(member.userId, userId)),
      ),
  });

  return otherOwners.length === 0;
};
