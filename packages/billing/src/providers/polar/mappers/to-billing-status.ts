import { BillingStatus } from "../../../types";

import type { OrderStatus } from "@polar-sh/sdk/models/components/orderstatus";
import type { SubscriptionStatus } from "@polar-sh/sdk/models/components/subscriptionstatus";

export const toBillingStatus = (status: SubscriptionStatus): BillingStatus => {
  switch (status) {
    case "active":
      return BillingStatus.ACTIVE;
    case "trialing":
      return BillingStatus.TRIALING;
    case "past_due":
      return BillingStatus.PAST_DUE;
    case "canceled":
      return BillingStatus.CANCELED;
    case "incomplete_expired":
      return BillingStatus.INCOMPLETE_EXPIRED;
    case "unpaid":
      return BillingStatus.UNPAID;
    case "incomplete":
      return BillingStatus.INCOMPLETE;
  }
};

export const toCheckoutBillingStatus = (status: OrderStatus): BillingStatus => {
  switch (status) {
    case "paid":
      return BillingStatus.ACTIVE;
    case "refunded":
    case "partially_refunded":
      return BillingStatus.CANCELED;
    case "pending":
      return BillingStatus.INCOMPLETE;
  }
};
