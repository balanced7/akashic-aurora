import { handle } from "hono/vercel";

import { appRouter } from "@akashic-labs/api";

const handler = handle(appRouter);
export {
  handler as GET,
  handler as POST,
  handler as OPTIONS,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
  handler as HEAD,
};
