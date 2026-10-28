import {
  billingStatusEnum,
  pricingPlanTypeEnum,
} from "@akashic-labs/db/schema";

import type {
  billingConfigSchema,
  discountSchema,
  planSchema,
  priceSchema,
} from "../config/schema";
import type { EnumToConstant } from "@akashic-labs/shared/types";
import type * as z from "zod";

export const BillingStatus = Object.fromEntries(
  Object.values(billingStatusEnum.enumValues).map((status) => [
    status.toUpperCase(),
    status,
  ]),
) as EnumToConstant<typeof billingStatusEnum.enumValues>;
export type BillingStatus = (typeof BillingStatus)[keyof typeof BillingStatus];

export const PricingPlanType = Object.fromEntries(
  Object.values(pricingPlanTypeEnum.enumValues).map((plan) => [
    plan.toUpperCase(),
    plan,
  ]),
) as EnumToConstant<typeof pricingPlanTypeEnum.enumValues>;
export type PricingPlanType =
  (typeof PricingPlanType)[keyof typeof PricingPlanType];

export const BillingModel = {
  ONE_TIME: "one-time",
  RECURRING: "recurring",
} as const;

export const RecurringInterval = {
  DAY: "day",
  MONTH: "month",
  WEEK: "week",
  YEAR: "year",
} as const;

export const BillingDiscountType = {
  PERCENT: "percent",
  AMOUNT: "amount",
} as const;

export const RecurringIntervalDuration: Record<RecurringInterval, number> = {
  [RecurringInterval.DAY]: 1,
  [RecurringInterval.WEEK]: 7,
  [RecurringInterval.MONTH]: 30,
  [RecurringInterval.YEAR]: 365,
};

export type BillingModel = (typeof BillingModel)[keyof typeof BillingModel];
export type RecurringInterval =
  (typeof RecurringInterval)[keyof typeof RecurringInterval];
export type BillingDiscountType =
  (typeof BillingDiscountType)[keyof typeof BillingDiscountType];

export type BillingConfig = z.infer<typeof billingConfigSchema>;
export type PricingPlan = z.infer<typeof planSchema>;
export type PricingPlanPrice = z.infer<typeof priceSchema>;
export type Discount = z.infer<typeof discountSchema>;

export type { SelectCustomer as Customer } from "@akashic-labs/db/schema";
