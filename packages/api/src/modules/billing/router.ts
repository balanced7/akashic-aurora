import { Hono } from "hono";

import {
  checkoutSchema,
  checkout,
  getBillingPortalSchema,
  getBillingPortal,
  webhookHandler,
  getCustomerByUserId,
} from "@akashic-labs/billing/server";

import { enforceAuth, validate } from "../../middleware";

export const billingRouter = new Hono()
  .post("/checkout", validate("json", checkoutSchema), enforceAuth, async (c) =>
    c.json(
      await checkout({
        user: c.var.user,
        ...c.req.valid("json"),
      }),
    ),
  )
  .get(
    "/portal",
    enforceAuth,
    validate("query", getBillingPortalSchema),
    async (c) =>
      c.json(
        await getBillingPortal({
          user: c.var.user,
          ...c.req.valid("query"),
        }),
      ),
  )
  .get("/customer", enforceAuth, async (c) =>
    c.json(await getCustomerByUserId(c.var.user.id)),
  )
  .post("/webhook", (c) => webhookHandler(c.req.raw));
