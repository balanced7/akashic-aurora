import { stripe } from "../client";

export const constructEvent = (data: {
  payload: string;
  sig: string;
  secret: string;
}) => {
  return stripe().webhooks.constructEvent(data.payload, data.sig, data.secret);
};
