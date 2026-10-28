import { eq } from "@akashic-labs/db";
import { organization } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

export const getOrganization = async ({ id }: { id: string }) =>
  db.query.organization.findFirst({
    where: eq(organization.id, id),
  });
