import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { checkoutStatusChangeHandler } from "../checkout";
import { env } from "../env";
import { subscriptionStatusChangeHandler } from "../subscription";

import { STRIPE_SIGNATURE_HEADER } from "./constants";
import { constructEvent } from "./event";

import type { BillingProviderStrategy } from "../../types";

export const webhookHandler: BillingProviderStrategy["webhookHandler"] = async (
  req,
  callbacks,
) => {
  const body = await req.text();
  const sig = req.headers.get(STRIPE_SIGNATURE_HEADER);

  if (!sig) {
    throw new HttpException(HttpStatusCode.BAD_REQUEST, {
      code: "billing:error.webhook.signatureNotFound",
    });
  }

  const event = constructEvent({
    payload: body,
    sig,
    secret: env.STRIPE_WEBHOOK_SECRET,
  });

  console.log(`🔔  Webhook received: ${event.type}`);
  await callbacks?.onEvent?.(event);

  switch (event.type) {
    case "customer.subscription.created":
      await callbacks?.onSubscriptionCreated?.(event.data.object.id);
      await subscriptionStatusChangeHandler({
        id: event.data.object.id,
        customerId: event.data.object.customer as string,
      });
      break;
    case "customer.subscription.updated":
      await callbacks?.onSubscriptionUpdated?.(event.data.object.id);
      await subscriptionStatusChangeHandler({
        id: event.data.object.id,
        customerId: event.data.object.customer as string,
      });
      break;
    case "customer.subscription.deleted":
      await callbacks?.onSubscriptionDeleted?.(event.data.object.id);
      await subscriptionStatusChangeHandler({
        id: event.data.object.id,
        customerId: event.data.object.customer as string,
      });
      break;
    case "checkout.session.completed":
      await callbacks?.onCheckoutSessionCompleted?.(event.data.object.id);
      await checkoutStatusChangeHandler(event.data.object);
      break;
  }

  return new Response(JSON.stringify({ received: true }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
};
