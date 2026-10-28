import { Hono } from "hono";

import { validate } from "../../../middleware";
import {
  getUserAccountsInputSchema,
  getUsersInputSchema,
  getUserMembershipsInputSchema,
  getUserInvitationsInputSchema,
  getUserPlansInputSchema,
} from "../../../schema";

import { deleteAccount } from "./mutations";
import {
  getUsers,
  getUserAccounts,
  getUserPlans,
  getUserMemberships,
  getUserInvitations,
} from "./queries";

export const usersRouter = new Hono()
  .get("/", validate("query", getUsersInputSchema), async (c) =>
    c.json(await getUsers(c.req.valid("query"))),
  )
  .get(
    "/:id/accounts",
    validate("query", getUserAccountsInputSchema),
    async (c) =>
      c.json(
        await getUserAccounts({
          userId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  )
  .get("/:id/plans", validate("query", getUserPlansInputSchema), async (c) =>
    c.json(
      await getUserPlans({
        userId: c.req.param("id"),
        ...c.req.valid("query"),
      }),
    ),
  )
  .get(
    "/:id/memberships",
    validate("query", getUserMembershipsInputSchema),
    async (c) =>
      c.json(
        await getUserMemberships({
          userId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  )
  .get(
    "/:id/invitations",
    validate("query", getUserInvitationsInputSchema),
    async (c) =>
      c.json(
        await getUserInvitations({
          userId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  )
  .delete("/:id/accounts/:accountId", async (c) =>
    c.json(await deleteAccount({ id: c.req.param("accountId") })),
  );
