import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { config } from "../../config";
import { getCustomerByCustomerId, updateCustomer } from "../../lib/customer";
import { getCustomerByUserId } from "../../server";
import { getHighestDiscountForPrice } from "../../utils";

import { polar } from "./client";
import { createOrRetrieveCustomer } from "./customer";
import { env } from "./env";
import { toCheckoutBillingStatus } from "./mappers/to-billing-status";
import { subscriptionStatusChangeHandler } from "./subscription";

import type { BillingProviderStrategy } from "../types";

const getPolarDiscountByCode = async (code: string) => {
  const discounts = await polar().discounts.list({
    query: code,
  });

  return discounts.result.items[0];
};

export const checkout: BillingProviderStrategy["checkout"] = async ({
  user,
  price: { id },
  redirect,
}) => {
  try {
    const plan = config.plans.find((plan) =>
      plan.prices.some((p) => p.id === id),
    );

    const price = plan?.prices.find((p) => p.id === id);

    if (!price || !plan) {
      throw new HttpException(HttpStatusCode.NOT_FOUND, {
        code: "billing:error.priceNotFound",
      });
    }

    const customer = await createOrRetrieveCustomer({
      email: user.email,
      id: user.id,
    });

    const discount = getHighestDiscountForPrice(price, config.discounts);
    const discountId = discount
      ? await getPolarDiscountByCode(discount.code)
      : undefined;

    const checkout = await polar().checkouts.create({
      products: [price.id],
      successUrl: redirect.success,
      customerId: customer.id,
      discountId: discountId?.id,
    });

    return { url: checkout.url };
  } catch {
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.checkout",
    });
  }
};

export const getBillingPortal: BillingProviderStrategy["getBillingPortal"] =
  async ({ user }) => {
    const defaultUrl = `https://polar.sh/${env.POLAR_ORGANIZATION_SLUG}/portal`;

    try {
      const customer = await getCustomerByUserId(user.id);

      if (!customer) {
        return {
          url: defaultUrl,
        };
      }

      const customerSession = await polar().customerSessions.create({
        customerId: customer.customerId,
      });

      return { url: customerSession.customerPortalUrl || defaultUrl };
    } catch {
      throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
        code: "billing:error.portal",
      });
    }
  };
export const checkoutStatusChangeHandler = async ({ id }: { id: string }) => {
  const order = await polar().orders.get({ id });

  const customer = await getCustomerByCustomerId(order.customerId);

  if (!customer) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  if (order.subscription) {
    await subscriptionStatusChangeHandler({
      id: order.subscription.id,
    });
    return;
  }

  const priceId = order.productId;
  const plan = config.plans.find((p) => p.prices.find((x) => x.id === priceId));

  await updateCustomer(customer.userId, {
    status: toCheckoutBillingStatus(order.status),
    ...(plan && { plan: plan.id }),
  });

  console.log(
    `✅ Checkout status changed for user ${customer.userId} to ${order.status}`,
  );
};
