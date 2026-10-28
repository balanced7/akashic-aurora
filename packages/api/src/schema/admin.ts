import * as z from "zod";

import {
  InvitationStatus,
  MemberRole,
  SocialProvider,
  UserRole,
} from "@akashic-labs/auth";
import { BillingStatus, PricingPlanType } from "@akashic-labs/billing";
import { updateCustomerSchema } from "@akashic-labs/db/schema";
import {
  offsetPaginationSchema,
  sortSchema,
} from "@akashic-labs/shared/schema";

export const getUsersInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  q: z.string().optional(),
  role: z
    .union([
      z.enum(UserRole).transform((val) => [val]),
      z.array(z.enum(UserRole)),
    ])
    .optional(),
  twoFactorEnabled: z
    .union([
      z.coerce.boolean().transform((val) => [val]),
      z.array(z.coerce.boolean()),
    ])
    .optional(),
  banned: z
    .union([
      z.coerce.boolean().transform((val) => [val]),
      z.array(z.coerce.boolean()),
    ])
    .optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetUsersInput = z.infer<typeof getUsersInputSchema>;

export const getUsersResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      createdAt: z.coerce.date(),
      updatedAt: z.coerce.date(),
      email: z.string(),
      emailVerified: z.boolean(),
      name: z.string(),
      image: z.string().nullish(),
      twoFactorEnabled: z.boolean().nullable(),
      isAnonymous: z.boolean(),
      banned: z.boolean().nullable(),
      role: z.string().nullish(),
      banReason: z.string().nullish(),
      banExpires: z.coerce.date().nullish(),
    }),
  ),
  total: z.number(),
});

export type GetUsersResponse = z.infer<typeof getUsersResponseSchema>;

export const getUserAccountsInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  providerId: z
    .union([
      z
        .enum(["credential", ...Object.values(SocialProvider)])
        .transform((val) => [val]),
      z.array(z.enum(["credential", ...Object.values(SocialProvider)])),
    ])
    .optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
  updatedAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetUserAccountsInput = z.infer<typeof getUserAccountsInputSchema>;

export const getUserPlansInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  plan: z
    .union([
      z.enum(PricingPlanType).transform((val) => [val]),
      z.array(z.enum(PricingPlanType)),
    ])
    .nullable()
    .optional(),
  status: z
    .union([
      z.enum(BillingStatus).transform((val) => [val]),
      z.array(z.enum(BillingStatus)),
    ])
    .nullable()
    .optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetUserPlansInput = z.infer<typeof getUserPlansInputSchema>;

export const getUserPlansResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      userId: z.string(),
      customerId: z.string(),
      plan: z.enum(PricingPlanType).nullable(),
      status: z.enum(BillingStatus).nullable(),
      createdAt: z.coerce.date(),
      updatedAt: z.coerce.date(),
      user: z.object({
        name: z.string(),
      }),
    }),
  ),
  total: z.number(),
});

export type GetUserPlansResponse = z.infer<typeof getUserPlansResponseSchema>;

export const getUserAccountsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      userId: z.string(),
      providerId: z.string(),
      accountId: z.string(),
      createdAt: z.coerce.date(),
      updatedAt: z.coerce.date(),
    }),
  ),
  total: z.number(),
});

export type GetUserAccountsResponse = z.infer<
  typeof getUserAccountsResponseSchema
>;

export const getUserMembershipsInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  role: z
    .union([
      z.enum(MemberRole).transform((val) => [val]),
      z.array(z.enum(MemberRole)),
    ])
    .optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetUserMembershipsInput = z.infer<
  typeof getUserMembershipsInputSchema
>;

export const getUserMembershipsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      organizationId: z.string(),
      role: z.enum(MemberRole),
      createdAt: z.coerce.date(),
      userId: z.string(),
      organization: z.object({
        id: z.string(),
        name: z.string(),
        slug: z.string().nullish(),
        logo: z.string().nullish(),
      }),
      user: z.object({
        id: z.string(),
        name: z.string(),
        email: z.string(),
      }),
    }),
  ),
  total: z.number(),
});

export type GetUserMembershipsResponse = z.infer<
  typeof getUserMembershipsResponseSchema
>;

export const getUserInvitationsInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
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
  expiresAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetUserInvitationsInput = z.infer<
  typeof getUserInvitationsInputSchema
>;

export const getUserInvitationsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      email: z.string(),
      role: z.enum(MemberRole),
      status: z.enum(InvitationStatus),
      expiresAt: z.coerce.date(),
      createdAt: z.coerce.date(),
      inviterId: z.string(),
      organizationId: z.string(),
      organization: z.object({
        id: z.string(),
        name: z.string(),
        logo: z.string().nullish(),
      }),
    }),
  ),
  total: z.number(),
});

export type GetUserInvitationsResponse = z.infer<
  typeof getUserInvitationsResponseSchema
>;

export const getOrganizationsInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  q: z.string().optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
  members: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetOrganizationsInput = z.infer<typeof getOrganizationsInputSchema>;

export const getOrganizationsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      slug: z.string().nullish(),
      logo: z.string().nullish(),
      createdAt: z.coerce.date(),
      members: z.number(),
    }),
  ),
  total: z.number(),
  max: z.object({
    members: z.number(),
  }),
});

export type GetOrganizationsResponse = z.infer<
  typeof getOrganizationsResponseSchema
>;

export const getOrganizationResponseSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    slug: z.string().nullish(),
    logo: z.string().nullish(),
    createdAt: z.coerce.date(),
  })
  .nullable();

export type GetOrganizationResponse = z.infer<
  typeof getOrganizationResponseSchema
>;

export const getCustomersInputSchema = offsetPaginationSchema.extend({
  sort: z
    .string()
    .transform((val) =>
      z.array(sortSchema).parse(JSON.parse(decodeURIComponent(val))),
    )
    .optional(),
  q: z.string().optional(),
  plan: z
    .union([
      z.enum(PricingPlanType).transform((val) => [val]),
      z.array(z.enum(PricingPlanType)),
    ])
    .optional(),
  status: z
    .union([
      z.enum(BillingStatus).transform((val) => [val]),
      z.array(z.enum(BillingStatus)),
    ])
    .optional(),
  createdAt: z.tuple([z.coerce.number(), z.coerce.number()]).optional(),
});

export type GetCustomersInput = z.infer<typeof getCustomersInputSchema>;

export const getCustomersResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
      customerId: z.string(),
      userId: z.string(),
      plan: z.enum(PricingPlanType).nullable(),
      status: z.enum(BillingStatus).nullable(),
      createdAt: z.coerce.date(),
      updatedAt: z.coerce.date(),
      user: z.object({
        name: z.string(),
        image: z.string().nullish(),
      }),
    }),
  ),
  total: z.number(),
});

export type GetCustomersResponse = z.infer<typeof getCustomersResponseSchema>;

export { updateCustomerSchema as updateCustomerInputSchema };
export type UpdateCustomerInput = z.infer<typeof updateCustomerSchema>;
