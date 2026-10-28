import * as z from "zod";

import { InvitationStatus, MemberRole } from "@akashic-labs/auth";
import {
  offsetPaginationSchema,
  sortSchema,
} from "@akashic-labs/shared/schema";

export const getMembersInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  q: z.string().optional(),
  role: z
    .union([
      z.enum(MemberRole).transform((val) => [val]),
      z.array(z.enum(MemberRole)),
    ])
    .optional(),
  createdAt: z.tuple([z.number(), z.number()]).optional(),
});

export type GetMembersInput = z.infer<typeof getMembersInputSchema>;

export const getMembersResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      organizationId: z.string(),
      role: z.enum(MemberRole),
      createdAt: z.coerce.date(),
      userId: z.string(),
      user: z.object({
        id: z.string(),
        name: z.string(),
        email: z.string(),
        image: z
          .string()
          .nullish()
          .transform((val) => (val === null ? undefined : val)),
      }),
    }),
  ),
  total: z.number(),
});

export type GetMembersResponse = z.infer<typeof getMembersResponseSchema>;

export const getInvitationsInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  email: z.string().optional(),
  role: z
    .union([
      z.enum(MemberRole).transform((val) => [val]),
      z.array(z.enum(MemberRole)),
    ])
    .optional(),
  status: z
    .union([
      z.enum(InvitationStatus).transform((val) => [val]),
      z.array(z.enum(InvitationStatus)),
    ])
    .optional(),
  expiresAt: z.tuple([z.number(), z.number()]).optional(),
});

export type GetInvitationsInput = z.infer<typeof getInvitationsInputSchema>;

export const getInvitationsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      organizationId: z.string(),
      email: z.string(),
      role: z.enum(MemberRole),
      expiresAt: z.coerce.date(),
      createdAt: z.coerce.date(),
      inviterId: z.string(),
      status: z.enum(InvitationStatus),
    }),
  ),
  total: z.number(),
});

export type GetInvitationsResponse = z.infer<
  typeof getInvitationsResponseSchema
>;
