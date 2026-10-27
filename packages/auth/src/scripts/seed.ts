import { eq } from "@akashic-labs/db";
import * as schema from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

import { env } from "../env";
import { generateName } from "../lib/utils";
import { auth } from "../server";
import { MemberRole, UserRole } from "../types";

const context = await auth.$context;

const SEED_PASSWORD_HASH = await context.password.hash(env.SEED_PASSWORD);

const getEmail = (suffix: string | string[]) => {
  const [name, domain] = env.SEED_EMAIL.split("@");

  return `${name}+${Array.isArray(suffix) ? suffix.join("-") : suffix}@${domain}`;
};

const getImage = (name: string) => `https://avatar.vercel.sh/${name}`;

const seedUser = async ({
  email,
  role = UserRole.USER,
}: {
  email: string;
  role?: UserRole;
}) => {
  const name = generateName(email);

  return await db.transaction(async (tx) => {
    const userId = context.generateId({ model: "user" }).toString();
    const userToInsert = {
      name,
      image: getImage(name),
      email,
      emailVerified: true,
      role,
    };

    const [user] = await tx
      .insert(schema.user)
      .values({ ...userToInsert, id: userId })
      .onConflictDoUpdate({
        target: schema.user.email,
        set: userToInsert,
      })
      .returning();

    if (!user) {
      return;
    }

    const alreadyExistingAccount = await tx.query.account.findFirst({
      where: (account, { eq, and }) =>
        and(eq(account.userId, user.id), eq(account.providerId, "credential")),
    });

    if (!alreadyExistingAccount) {
      const accountToInsert = {
        id: context.generateId({ model: "account" }).toString(),
        accountId: context.generateId({ model: "account" }).toString(),
        providerId: "credential",
        password: SEED_PASSWORD_HASH,
        userId: user.id,
      };

      await tx.insert(schema.account).values(accountToInsert);
    }

    return user;
  });
};

const seedOrganizationMember = async ({
  organizationId,
  role,
}: {
  organizationId: string;
  role: MemberRole;
}) =>
  db.transaction(async (tx) => {
    const email = getEmail([`org`, role]);
    const user = await seedUser({ email });

    if (!user) {
      return;
    }

    const memberToInsert = {
      id: context.generateId({ model: "member" }).toString(),
      organizationId,
      role,
      userId: user.id,
      createdAt: new Date(),
    };

    const alreadyExistingMember = await tx.query.member.findFirst({
      where: (member, { eq, and }) =>
        and(
          eq(member.userId, memberToInsert.userId),
          eq(member.organizationId, memberToInsert.organizationId),
        ),
    });

    if (alreadyExistingMember) {
      const [updatedMember] = await tx
        .update(schema.member)
        .set(memberToInsert)
        .where(eq(schema.member.id, alreadyExistingMember.id))
        .returning();

      return updatedMember;
    }

    const [member] = await tx
      .insert(schema.member)
      .values(memberToInsert)
      .returning();

    return member;
  });

const seedOrganizationInvitation = async ({
  organizationId,
  inviterId,
  role,
}: {
  organizationId: string;
  inviterId: string;
  role: MemberRole;
}) =>
  db.transaction(async (tx) => {
    const invitationToInsert = {
      id: context.generateId({ model: "invitation" }).toString(),
      organizationId,
      role,
      email: getEmail([`org`, `invite`, role]),
      expiresAt: new Date(
        Date.now() +
          (Math.random() < 0.5 ? -1 : 1) *
            Math.floor(Math.random() * 1000 * 60 * 60 * 24),
      ),
      inviterId,
    };

    const alreadyExistingInvitation = await tx.query.invitation.findFirst({
      where: (invitation, { eq, and }) =>
        and(
          eq(invitation.organizationId, invitationToInsert.organizationId),
          eq(invitation.email, invitationToInsert.email),
        ),
    });

    if (alreadyExistingInvitation) {
      const [updatedInvitation] = await tx
        .update(schema.invitation)
        .set(invitationToInsert)
        .where(eq(schema.invitation.id, alreadyExistingInvitation.id))
        .returning();
      return updatedInvitation;
    }

    const [invitation] = await tx
      .insert(schema.invitation)
      .values(invitationToInsert)

      .returning();

    return invitation;
  });

const seedOrganization = async () => {
  const organizationId = context
    .generateId({ model: "organization" })
    .toString();
  const organizationSlug = "seed-organization";

  const organizationToInsert = {
    name: organizationSlug,
    slug: organizationSlug,
    logo: getImage(organizationSlug),
    createdAt: new Date(),
  };

  const [organization] = await db
    .insert(schema.organization)
    .values({ ...organizationToInsert, id: organizationId })
    .onConflictDoUpdate({
      target: schema.organization.slug,
      set: organizationToInsert,
    })
    .returning();

  if (!organization) {
    return;
  }

  const members = await Promise.all(
    Object.values(MemberRole).map((role) =>
      seedOrganizationMember({ organizationId: organization.id, role }),
    ),
  );

  await Promise.all(
    members.flatMap((member) =>
      Object.values(MemberRole)
        .filter((role) => role !== MemberRole.OWNER)
        .map((role) =>
          seedOrganizationInvitation({
            organizationId: organization.id,
            role,
            inviterId: member?.userId ?? "",
          }),
        ),
    ),
  );

  return organization;
};

const seedUsers = async () =>
  Promise.all(
    Object.values(UserRole).map((role) =>
      seedUser({ email: getEmail(role), role }),
    ),
  );

async function main() {
  await seedUsers();
  await seedOrganization();

  console.log("Auth seeded successfully");
  process.exit(0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
