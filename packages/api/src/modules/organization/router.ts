import { Hono } from "hono";
import * as z from "zod";

import { MemberRole } from "@akashic-labs/auth";

import { enforceAuth, enforceMembership, validate } from "../../middleware";
import { getInvitationsInputSchema, getMembersInputSchema } from "../../schema";

import { generateSlug } from "./queries/generate-slug";
import { getInvitations } from "./queries/invitations";
import { getIsOnlyOwner, getMembers } from "./queries/members";
import { getOrganization } from "./queries/organizations";

export const organizationRouter = new Hono()
  .use(enforceAuth)
  .get(
    "/slug",
    validate(
      "query",
      z.object({
        name: z.string(),
      }),
    ),
    async (c) => c.json(await generateSlug(c.req.valid("query").name)),
  )
  .get("/:id", async (c) =>
    c.json({ organization: await getOrganization({ id: c.req.param("id") }) }),
  )
  .get(
    "/:id/members",
    validate("query", getMembersInputSchema),
    (c, next) =>
      enforceMembership({ organizationId: c.req.param("id") })(c, next),
    async (c) =>
      c.json(
        await getMembers({
          organizationId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  )
  .get(
    "/:id/members/is-only-owner",
    (c, next) =>
      enforceMembership({
        organizationId: c.req.param("id"),
        role: MemberRole.OWNER,
      })(c, next),
    async (c) =>
      c.json({
        status: await getIsOnlyOwner({
          organizationId: c.req.param("id"),
          userId: c.var.user.id,
        }),
      }),
  )
  .get(
    "/:id/invitations",
    validate("query", getInvitationsInputSchema),
    (c, next) =>
      enforceMembership({ organizationId: c.req.param("id") })(c, next),
    async (c) =>
      c.json(
        await getInvitations({
          organizationId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  );
