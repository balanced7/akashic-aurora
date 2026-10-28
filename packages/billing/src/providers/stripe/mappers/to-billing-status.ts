import { BillingStatus } from "../../../types";

export const toBillingStatus = (status: string): BillingStatus => {
  switch (status) {
    case "active":
      return BillingStatus.ACTIVE;
    case "trialing":
      return BillingStatus.TRIALING;
    case "past_due":
      return BillingStatus.PAST_DUE;
    case "incomplete":
      return BillingStatus.INCOMPLETE;
    case "incomplete_expired":
      return BillingStatus.INCOMPLETE_EXPIRED;
    case "canceled":
      return BillingStatus.CANCELED;
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
    case "open":
      return BillingStatus.PAUSED;
    case "complete":
      return BillingStatus.ACTIVE;
    case "expired":
      return BillingStatus.CANCELED;
    default:
      throw new Error(`Invalid checkout billing status: ${status}`);
  }
};

export const toPaymentBillingStatus = (status: string): BillingStatus => {
  switch (status) {
    case "paid":
      return BillingStatus.ACTIVE;
    case "unpaid":
      return BillingStatus.UNPAID;
    case "no_payment_required":
      return BillingStatus.ACTIVE;
    default:
      throw new Error(`Invalid payment billing status: ${status}`);
  }
};
