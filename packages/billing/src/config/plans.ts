import {
  BillingModel,
  PricingPlanType,
  RecurringInterval,
  BillingDiscountType,
} from "../types";

import type { Discount } from "../types";

export const plans = [
  {
    id: PricingPlanType.FREE,
    name: "plan.starter.name",
    description: "plan.starter.description",
    badge: null,
    prices: [
      {
        id: "starter-lifetime",
        amount: 0,
        type: BillingModel.ONE_TIME,
      },
      {
        id: "starter-monthly",
        amount: 0,
        interval: RecurringInterval.MONTH,
        type: BillingModel.RECURRING,
      },
      {
        id: "starter-yearly",
        amount: 0,
        interval: RecurringInterval.YEAR,
        type: BillingModel.RECURRING,
      },
    ],
  },
  {
    id: PricingPlanType.PREMIUM,
    name: "plan.premium.name",
    description: "plan.premium.description",
    badge: "plan.premium.badge",
    prices: [
      {
        id: "price_1PpUagFQH4McJDTlHCzOmyT6",
        amount: 29900,
        type: BillingModel.ONE_TIME,
      },
      {
        id: "price_1PpZAAFQH4McJDTlig6FBPyy",
        amount: 1900,
        interval: RecurringInterval.MONTH,
        trialDays: 7,
        type: BillingModel.RECURRING,
      },
      {
        id: "price_1PpZALFQH4McJDTl8SWorWTO",
        amount: 8900,
        interval: RecurringInterval.YEAR,
        trialDays: 7,
        type: BillingModel.RECURRING,
      },
    ],
  },
  {
    id: PricingPlanType.ENTERPRISE,
    name: "plan.enterprise.name",
    description: "plan.enterprise.description",
    badge: null,
    prices: [
      {
        id: "enterprise-lifetime",
        label: "common:contactUs",
        href: "/contact",
        type: BillingModel.ONE_TIME,
        custom: true,
      },
      {
        id: "enterprise-monthly",
        label: "common:contactUs",
        href: "/contact",
        type: BillingModel.RECURRING,
        interval: RecurringInterval.MONTH,
        custom: true,
      },
      {
        id: "enterprise-yearly",
        label: "common:contactUs",
        href: "/contact",
        type: BillingModel.RECURRING,
        interval: RecurringInterval.YEAR,
        custom: true,
      },
    ],
  },
];

export const discounts: Discount[] = [
  {
    code: "50OFF",
    type: BillingDiscountType.PERCENT,
    off: 50,
    appliesTo: [
      "price_1PpUagFQH4McJDTlHCzOmyT6",
      "price_1PpZAAFQH4McJDTlig6FBPyy",
      "price_1PpZALFQH4McJDTl8SWorWTO",
    ],
  },
];
