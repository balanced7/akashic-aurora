import { Hono } from "hono";

import {
  updateMemberSchema,
  updateOrganizationSchema,
} from "@akashic-labs/auth";

import { validate } from "../../../middleware";
import {
  getInvitationsInputSchema,
  getMembersInputSchema,
  getOrganizationsInputSchema,
} from "../../../schema";
import { getInvitations } from "../../organization/queries/invitations";
import { getMembers } from "../../organization/queries/members";

import {
  deleteOrganization,
  deleteOrganizationInvitation,
  deleteOrganizationMember,
  updateOrganizationMember,
} from "./mutations";
import { updateOrganization } from "./mutations";
import { getOrganizations, getOrganization } from "./queries";

export const organizationsRouter = new Hono()
  .get("/", validate("query", getOrganizationsInputSchema), async (c) =>
    c.json(await getOrganizations(c.req.valid("query"))),
  )
  .get("/:id", async (c) =>
    c.json(await getOrganization({ id: c.req.param("id") })),
  )
  .delete("/:id", async (c) =>
    c.json(await deleteOrganization({ id: c.req.param("id") })),
  )
  .patch("/:id", validate("json", updateOrganizationSchema), async (c) =>
    c.json(
      await updateOrganization({
        id: c.req.param("id"),
        data: c.req.valid("json"),
      }),
    ),
  )
  .get("/:id/members", validate("query", getMembersInputSchema), async (c) =>
    c.json(
      await getMembers({
        organizationId: c.req.param("id"),
        ...c.req.valid("query"),
      }),
    ),
  )
  .patch(
    "/:id/members/:memberId",
    validate("json", updateMemberSchema),
    async (c) =>
      c.json(
        await updateOrganizationMember({
          id: c.req.param("memberId"),
          data: c.req.valid("json"),
        }),
      ),
  )
  .delete("/:id/members/:memberId", async (c) =>
    c.json(
      await deleteOrganizationMember({
        id: c.req.param("memberId"),
        organizationId: c.req.param("id"),
      }),
    ),
  )
  .get(
    "/:id/invitations",
    validate("query", getInvitationsInputSchema),
    async (c) =>
      c.json(
        await getInvitations({
          organizationId: c.req.param("id"),
          ...c.req.valid("query"),
        }),
      ),
  )
  .delete("/:id/invitations/:invitationId", async (c) =>
    c.json(
      await deleteOrganizationInvitation({
        id: c.req.param("invitationId"),
        organizationId: c.req.param("id"),
      }),
    ),
  );
