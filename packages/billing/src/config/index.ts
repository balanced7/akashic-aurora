import { BillingStatus } from "../types";

import { discounts, plans } from "./plans";
import { billingConfigSchema } from "./schema";

import type { BillingConfig } from "../types";

export const config = billingConfigSchema.parse({
  plans,
  discounts,
}) satisfies BillingConfig;

export const ACTIVE_BILLING_STATUSES: BillingStatus[] = [
  BillingStatus.ACTIVE,
  BillingStatus.TRIALING,
];

export * from "./features";
