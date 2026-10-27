import * as z from "zod";

export const checkoutSchema = z.object({
  price: z.object({
    id: z.string(),
  }),
  redirect: z.object({
    success: z.url(),
    cancel: z.url(),
  }),
});

export const getBillingPortalSchema = z.object({
  redirectUrl: z.url(),
});

export type CheckoutPayload = z.infer<typeof checkoutSchema>;
export type GetBillingPortalPayload = z.infer<typeof getBillingPortalSchema>;
