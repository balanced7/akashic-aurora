import { Hono } from "hono";

import { validate } from "../../../middleware";
import {
  getCustomersInputSchema,
  updateCustomerInputSchema,
} from "../../../schema";

import { deleteCustomer, updateCustomer } from "./mutations";
import { getCustomers } from "./queries";

export const customersRouter = new Hono()
  .get("/", validate("query", getCustomersInputSchema), async (c) =>
    c.json(await getCustomers(c.req.valid("query"))),
  )
  .patch("/:id", validate("json", updateCustomerInputSchema), async (c) =>
    c.json(
      await updateCustomer({
        id: c.req.param("id"),
        data: c.req.valid("json"),
      }),
    ),
  )
  .delete("/:id", async (c) =>
    c.json(await deleteCustomer({ id: c.req.param("id") })),
  );
