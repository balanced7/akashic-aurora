import dayjs from "dayjs";

import {
  and,
  asc,
  between,
  count,
  eq,
  getOrderByFromSort,
  ilike,
  sql,
} from "@akashic-labs/db";
import { organization, member } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import type { GetOrganizationsInput } from "../../../schema";

export const getOrganizationsCount = async () =>
  db
    .select({ count: count() })
    .from(organization)
    .then((res) => res[0]?.count ?? 0);

export const getOrganizations = async (input: GetOrganizationsInput) => {
  const offset = (input.page - 1) * input.perPage;

  const where = and(
    input.q ? ilike(organization.name, `%${input.q}%`) : undefined,
    input.createdAt
      ? between(
          organization.createdAt,
          dayjs(input.createdAt[0]).startOf("day").toDate(),
          dayjs(input.createdAt[1]).endOf("day").toDate(),
        )
      : undefined,
  );

  const having = input.members
    ? between(
        sql<number>`CAST(COUNT(${member.id}) AS INTEGER)`,
        input.members[0],
        input.members[1],
      )
    : undefined;

  const orderBy =
    input.sort && input.sort.length > 0
      ? input.sort.flatMap((s) => {
          const field = s.id.split(/[_.]/).pop() ?? s.id;
          if (field === "members") {
            return [s.desc ? sql`members DESC` : sql`members ASC`];
          }
          return getOrderByFromSort({ sort: [s], defaultSchema: organization });
        })
      : [asc(organization.name)];

  return db.transaction(async (tx) => {
    const results = await tx
      .select({
        id: organization.id,
        name: organization.name,
        slug: organization.slug,
        logo: organization.logo,
        createdAt: organization.createdAt,
        members: sql<number>`CAST(COUNT(${member.id}) AS INTEGER)`.as(
          "members",
        ),
        total: sql<number>`COUNT(*) OVER()`.mapWith(Number).as("total"),
      })
      .from(organization)
      .leftJoin(member, eq(member.organizationId, organization.id))
      .where(where)
      .groupBy(organization.id)
      .having(having)
      .limit(input.perPage)
      .offset(offset)
      .orderBy(...orderBy);

    const membersMax = await tx
      .select({
        members: sql<number>`CAST(COUNT(${member.id}) AS INTEGER)`.as(
          "members",
        ),
      })
      .from(member)
      .groupBy(member.organizationId)
      .orderBy(sql`members DESC`)
      .limit(1)
      .then((res) => res[0]?.members ?? 0);

    const data = results.map(({ total: _, ...rest }) => rest);
    const total = results[0]?.total ?? 0;

    return {
      data,
      total,
      max: { members: membersMax },
    };
  });
};

export const getOrganization = async ({ id }: { id: string }) => {
  return (
    (await db.query.organization.findFirst({
      where: eq(organization.id, id),
    })) ?? null
  );
};
