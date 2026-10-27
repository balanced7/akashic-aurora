import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { config } from "../../config";
import { getCustomerByCustomerId, updateCustomer } from "../../lib/customer";
import { BillingModel } from "../../types";
import { getHighestDiscountForPrice } from "../../utils";

import { stripe } from "./client";
import {
  createBillingPortalSession,
  createOrRetrieveCustomer,
} from "./customer";
import { env } from "./env";
import {
  toCheckoutBillingStatus,
  toPaymentBillingStatus,
} from "./mappers/to-billing-status";
import {
  getPromotionCode,
  subscriptionStatusChangeHandler,
} from "./subscription";

import type { BillingProviderStrategy } from "../types";
import type Stripe from "stripe";

const createCheckoutSession = async (
  params: Stripe.Checkout.SessionCreateParams,
) => {
  try {
    return await stripe().checkout.sessions.create(params);
  } catch (e) {
    console.error(e);
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.checkout",
    });
  }
};

const getCheckoutSession = async (sessionId: string) => {
  try {
    return await stripe().checkout.sessions.retrieve(sessionId, {
      expand: ["line_items", "line_items.data.price"],
    });
  } catch (e) {
    console.error(e);
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.checkoutRetrieve",
    });
  }
};

export const checkoutStatusChangeHandler = async (
  session: Stripe.Checkout.Session,
) => {
  const customerId = session.customer as string | null;

  if (!customerId) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  if (session.mode === "subscription") {
    await subscriptionStatusChangeHandler({
      id: session.subscription as string,
      customerId,
    });
    return;
  }

  const customer = await getCustomerByCustomerId(customerId);

  if (!customer) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.customerNotFound",
    });
  }

  const checkoutSession = await getCheckoutSession(session.id);
  const priceId = checkoutSession.line_items?.data[0]?.price?.id;

  if (!priceId) {
    throw new HttpException(HttpStatusCode.NOT_FOUND, {
      code: "billing:error.priceNotFound",
    });
  }

  const plan = config.plans.find((p) =>
    p.prices.some((price) => price.id === priceId),
  );

  await updateCustomer(customer.userId, {
    status: checkoutSession.status
      ? toCheckoutBillingStatus(checkoutSession.status)
      : toPaymentBillingStatus(checkoutSession.payment_status),
    ...(plan && { plan: plan.id }),
  });

  console.log(
    `✅ Checkout status changed for user ${customer.userId} to ${checkoutSession.status}`,
  );
};

export const checkout: BillingProviderStrategy["checkout"] = async ({
  user,
  price: { id },
  redirect,
}) => {
  try {
    const price = config.plans
      .find((plan) => plan.prices.some((p) => p.id === id))
      ?.prices.find((p) => p.id === id);

    if (!price) {
      throw new HttpException(HttpStatusCode.NOT_FOUND, {
        code: "billing:error.priceNotFound",
      });
    }

    const customer = await createOrRetrieveCustomer({
      email: user.email,
      id: user.id,
    });

    const discount = getHighestDiscountForPrice(price, config.discounts);
    const code = await getPromotionCode(discount?.code ?? "");

    const session = await createCheckoutSession({
      mode:
        env.BILLING_MODEL === BillingModel.RECURRING
          ? "subscription"
          : "payment",
      billing_address_collection: "required",
      customer,
      customer_update: {
        address: "auto",
      },
      line_items: [
        {
          price: price.id,
          quantity: 1,
        },
      ],
      success_url: redirect.success,
      cancel_url: redirect.cancel,
      ...("trialDays" in price && price.trialDays
        ? {
            subscription_data: {
              trial_period_days: price.trialDays,
            },
          }
        : {}),
      ...(code && {
        discounts: [
          {
            promotion_code: code.id,
          },
        ],
      }),
    });

    return { url: session.url };
  } catch {
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR);
  }
};

export const getBillingPortal: BillingProviderStrategy["getBillingPortal"] =
  async ({ redirectUrl, user }) => {
    try {
      const customer = await createOrRetrieveCustomer({
        email: user.email,
        id: user.id,
      });

      const { url } = await createBillingPortalSession({
        customer,
        return_url: redirectUrl,
      });

      return { url };
    } catch {
      throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR);
    }
  };
