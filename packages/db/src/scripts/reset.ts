import { reset } from "drizzle-seed";

import * as schema from "../schema";
import { db } from "../server";

async function main() {
  await reset(db, schema);

  console.log("Database reset successfully!");
  process.exit(0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
