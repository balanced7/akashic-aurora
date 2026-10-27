import { BillingStatus } from "../../../types";

export const toBillingStatus = (status: string): BillingStatus => {
  switch (status) {
    case "active":
      return BillingStatus.ACTIVE;
    case "on_trial":
      return BillingStatus.TRIALING;
    case "past_due":
      return BillingStatus.PAST_DUE;
    case "cancelled":
      return BillingStatus.CANCELED;
    case "expired":
      return BillingStatus.INCOMPLETE_EXPIRED;
    case "unpaid":
      return BillingStatus.UNPAID;
    case "paused":
      return BillingStatus.PAUSED;

    default:
      throw new Error(`Invalid billing status: ${status}`);
  }
};

export const toCheckoutBillingStatus = (status: string): BillingStatus => {
  switch (status) {
    case "paid":
      return BillingStatus.ACTIVE;
    case "refunded":
      return BillingStatus.CANCELED;
    case "failed":
      return BillingStatus.UNPAID;
    case "pending":
      return BillingStatus.INCOMPLETE;
    default:
      throw new Error(`Invalid checkout billing status: ${status}`);
  }
};
