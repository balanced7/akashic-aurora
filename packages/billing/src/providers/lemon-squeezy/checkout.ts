import {
  createCheckout,
  getCustomer,
  getOrder,
} from "@lemonsqueezy/lemonsqueezy.js";

import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { config } from "../../config";
import { getCustomerByCustomerId, updateCustomer } from "../../lib/customer";
import { getCustomerByUserId } from "../../server";
import { getHighestDiscountForPrice } from "../../utils";

import { createOrRetrieveCustomer } from "./customer";
import { env } from "./env";
import { toCheckoutBillingStatus } from "./mappers/to-billing-status";

import type { BillingProviderStrategy } from "../types";

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

    const session = await createCheckout(env.LEMON_SQUEEZY_STORE_ID, id, {
      checkoutData: {
        email: customer.attributes.email,
        name: customer.attributes.name,
        custom: {
          user_id: user.id,
        },
        ...(discount && { discountCode: discount.code }),
      },
      productOptions: {
        enabledVariants: [Number(id)],
        redirectUrl: redirect.success,
      },
    });

    return { url: session.data?.data.attributes.url ?? null };
  } catch {
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.checkout",
    });
  }
};

export const getBillingPortal: BillingProviderStrategy["getBillingPortal"] =
  async ({ user }) => {
    const defaultUrl = `https://${env.LEMON_SQUEEZY_STORE_ID}.lemonsqueezy.com/billing`;

    try {
      const customer = await getCustomerByUserId(user.id);

      if (!customer) {
        return {
          url: defaultUrl,
        };
      }

      const lemonCustomer = await getCustomer(customer.customerId);

      const url = lemonCustomer.data?.data.attributes.urls.customer_portal;

      return { url: url ?? defaultUrl };
    } catch {
      throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
        code: "billing:error.portal",
      });
    }
  };

export const checkoutStatusChangeHandler = async ({ id }: { id: string }) => {
  const { data } = await getOrder(id);

  const order = data?.data;

  if (!order) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.orderNotFound",
    });
  }

  const customer = await getCustomerByCustomerId(
    order.attributes.customer_id.toString(),
  );

  if (!customer) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  const priceId = order.attributes.first_order_item.variant_id.toString();
  const plan = config.plans.find((p) => p.prices.find((x) => x.id === priceId));

  await updateCustomer(customer.userId, {
    status: toCheckoutBillingStatus(order.attributes.status),
    ...(plan && { plan: plan.id }),
  });

  console.log(
    `✅ Checkout status changed for user ${customer.userId} to ${order.attributes.status}`,
  );
};
