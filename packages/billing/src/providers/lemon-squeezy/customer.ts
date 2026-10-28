import {
  createCustomer,
  getCustomer,
  listCustomers,
} from "@lemonsqueezy/lemonsqueezy.js";

import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { updateCustomer, upsertCustomer } from "../../lib/customer";
import { getCustomerByUserId } from "../../server";

import { env } from "./env";

const getLemonSqueezyCustomerById = async (customerId: string) => {
  return getCustomer(customerId);
};

const getLemonSqueezyCustomerByEmail = async (email: string) => {
  const { data } = await listCustomers({
    filter: {
      email: email,
    },
  });

  return data?.data[0];
};

const createLemonSqueezyCustomer = async (email: string) => {
  const newCustomer = await createCustomer(env.LEMON_SQUEEZY_STORE_ID, {
    name: email.split("@")[0] ?? "",
    email: email,
  });

  return newCustomer.data?.data;
};

export const createOrRetrieveCustomer = async ({
  email,
  id,
}: {
  email: string;
  id: string;
}) => {
  const existingCustomer = await getCustomerByUserId(id);

  const lemonSqueezyCustomer = existingCustomer?.customerId
    ? (await getLemonSqueezyCustomerById(existingCustomer.customerId)).data
        ?.data
    : await getLemonSqueezyCustomerByEmail(email);

  const lemonSqueezyCustomerToProcess =
    lemonSqueezyCustomer ?? (await createLemonSqueezyCustomer(email));

  if (!lemonSqueezyCustomerToProcess) {
    throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
      code: "billing:error.customerCreation",
    });
  }

  if (existingCustomer && lemonSqueezyCustomer) {
    if (existingCustomer.customerId !== lemonSqueezyCustomer.id) {
      await updateCustomer(id, {
        customerId: lemonSqueezyCustomerToProcess.id,
      });
      console.warn(
        `Customer ${id} had a different customerId. Updated to ${lemonSqueezyCustomerToProcess.id}.`,
      );
    }

    return lemonSqueezyCustomerToProcess;
  }

  await upsertCustomer({
    userId: id,
    customerId: lemonSqueezyCustomerToProcess.id,
  });

  return lemonSqueezyCustomerToProcess;
};
