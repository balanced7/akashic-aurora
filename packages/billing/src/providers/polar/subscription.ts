import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { config } from "../../config";
import { getCustomerByCustomerId, updateCustomer } from "../../lib/customer";

import { polar } from "./client";
import { toBillingStatus } from "./mappers/to-billing-status";

export const subscriptionStatusChangeHandler = async ({
  id,
}: {
  id: string;
}) => {
  const subscription = await polar().subscriptions.get({ id });

  const customer = await getCustomerByCustomerId(subscription.customerId);

  if (!customer) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  const priceId = subscription.productId;
  const plan = config.plans.find((p) => p.prices.find((x) => x.id === priceId));

  await updateCustomer(customer.userId, {
    status: toBillingStatus(subscription.status),
    ...(plan && { plan: plan.id }),
  });

  console.log(
    `✅ Subscription status changed for user ${customer.userId} to ${subscription.status}`,
  );
};
