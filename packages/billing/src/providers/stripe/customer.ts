import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import {
  getCustomerByUserId,
  updateCustomer,
  upsertCustomer,
} from "../../lib/customer";

import { stripe } from "./client";

import type Stripe from "stripe";

const getStripeCustomerById = async (stripeId: string) => {
  return stripe().customers.retrieve(stripeId);
};

const getStripeCustomerByEmail = async (email: string) => {
  const customers = await stripe().customers.list({ email: email });

  return customers.data.length > 0 ? customers.data[0] : null;
};

const createStripeCustomer = async (id: string, email: string) => {
  const customerData = { metadata: { userId: id }, email: email };
  const newCustomer = await stripe().customers.create(customerData);

  return newCustomer.id;
};

export const createOrRetrieveCustomer = async ({
  email,
  id,
}: {
  email: string;
  id: string;
}) => {
  const existingCustomer = await getCustomerByUserId(id);

  const stripeCustomerId = existingCustomer?.customerId
    ? (await getStripeCustomerById(existingCustomer.customerId)).id
    : (await getStripeCustomerByEmail(email))?.id;

  const stripeIdToInsert =
    stripeCustomerId ?? (await createStripeCustomer(id, email));

  if (!stripeIdToInsert) {
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.customerCreation",
    });
  }

  if (existingCustomer && stripeCustomerId) {
    if (existingCustomer.customerId !== stripeCustomerId) {
      await updateCustomer(id, {
        customerId: stripeCustomerId,
      });
      console.warn(
        `Customer ${id} had a different customerId. Updated to ${stripeCustomerId}.`,
      );
    }

    return stripeCustomerId;
  }

  await upsertCustomer({
    userId: id,
    customerId: stripeIdToInsert,
  });

  return stripeIdToInsert;
};

export const createBillingPortalSession = async (
  params: Stripe.BillingPortal.SessionCreateParams,
) => {
  try {
    return await stripe().billingPortal.sessions.create(params);
  } catch (e) {
    console.error(e);
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.portal",
    });
  }
};
