import * as z from "zod";

import {
  BillingDiscountType,
  BillingModel,
  PricingPlanType,
  RecurringInterval,
} from "../types";

export const discountSchema = z.object({
  code: z.string(),
  type: z.enum(BillingDiscountType),
  off: z.number(),
  appliesTo: z.array(z.string()),
});

const customPriceSchema = z.union([
  z.object({
    custom: z.literal(true),
    label: z.string(),
    href: z.string(),
  }),
  z.object({
    custom: z.literal(false).optional().default(false),
    amount: z.number(),
  }),
]);

const sharedPriceSchema = z.intersection(
  customPriceSchema,
  z.object({
    id: z.string(),
    currency: z.string().optional(),
  }),
);

const priceTypeSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal(BillingModel.ONE_TIME),
  }),
  z.object({
    type: z.literal(BillingModel.RECURRING),
    interval: z.enum(RecurringInterval),
    trialDays: z.number().optional(),
  }),
]);

export const priceSchema = z.intersection(sharedPriceSchema, priceTypeSchema);

export const planSchema = z.object({
  id: z.enum(PricingPlanType),
  name: z.string(),
  description: z.string(),
  badge: z.string().nullable().default(null),
  prices: z.array(priceSchema),
});

export const billingConfigSchema = z.object({
  plans: z.array(planSchema).refine(
    (plans) => {
      const types = new Set(plans.map((plan) => plan.id));
      return types.size === plans.length;
    },
    {
      message: "You can't have two plans with the same id!",
    },
  ),
  discounts: z.array(discountSchema).optional().default([]),
});
