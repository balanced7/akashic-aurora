import Stripe from "stripe";

import { env } from "./env";

let stripeInstance: Stripe | null = null;

export const stripe = () => {
  stripeInstance ??= new Stripe(env.STRIPE_SECRET_KEY);

  return stripeInstance;
};
