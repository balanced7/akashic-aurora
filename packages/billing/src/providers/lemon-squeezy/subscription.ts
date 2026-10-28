import { getSubscription } from "@lemonsqueezy/lemonsqueezy.js";

import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { config } from "../../config";
import { getCustomerByCustomerId, updateCustomer } from "../../lib/customer";

import { toBillingStatus } from "./mappers/to-billing-status";

export const subscriptionStatusChangeHandler = async ({
  id,
}: {
  id: string;
}) => {
  const { data } = await getSubscription(id);

  const subscription = data?.data;

  if (!subscription) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.subscriptionNotFound",
    });
  }

  const customer = await getCustomerByCustomerId(
    subscription.attributes.customer_id.toString(),
  );

  if (!customer) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  const priceId = subscription.attributes.variant_id.toString();
  const plan = config.plans.find((p) => p.prices.find((x) => x.id === priceId));

  await updateCustomer(customer.userId, {
    status: toBillingStatus(subscription.attributes.status),
    ...(plan && { plan: plan.id }),
  });

  console.log(
    `✅ Subscription status changed for user ${customer.userId} to ${subscription.attributes.status}`,
  );
};
