import { Hono } from "hono";
import { some } from "hono/combine";
import { cors } from "hono/cors";
import { csrf } from "hono/csrf";
import { logger } from "hono/logger";

import { auth } from "@akashic-labs/auth/server";
import { matchesPattern } from "@akashic-labs/shared/utils";

import { localize, timing } from "./middleware";
import { adminRouter } from "./modules/admin/router";
import { aiRouter } from "./modules/ai/router";
import { authRouter } from "./modules/auth/router";
import { billingRouter } from "./modules/billing/router";
import { organizationRouter } from "./modules/organization/router";
import { storageRouter } from "./modules/storage/router";
import { onError } from "./utils/on-error";

import type { Context } from "hono";

const appRouter = new Hono()
  .basePath("/api")
  .use(logger())
  .use(
    some(
      (c: Context) => !!c.req.header("x-client-platform")?.startsWith("mobile"),
      csrf({
        origin: (origin, c) =>
          [...auth.options.trustedOrigins, new URL(c.req.url).origin].some(
            (trustedOrigin) => matchesPattern(origin, trustedOrigin),
          ),
      }),
    ),
  )
  .use(
    cors({
      origin: "*",
      allowHeaders: ["Content-Type", "Authorization"],
      maxAge: 3600,
      credentials: true,
    }),
  )
  .use(timing)
  .use(localize)
  .route("/admin", adminRouter)
  .route("/ai", aiRouter)
  .route("/auth", authRouter)
  .route("/billing", billingRouter)
  .route("/organizations", organizationRouter)
  .route("/storage", storageRouter)
  .onError(onError);

type AppRouter = typeof appRouter;

export type { AppRouter };
export { appRouter };
