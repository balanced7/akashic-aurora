import { eq } from "@akashic-labs/db";
import { account } from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";

export const deleteAccount = async ({ id }: { id: string }) =>
  db.delete(account).where(eq(account.id, id));
