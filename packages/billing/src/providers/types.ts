import type { CheckoutPayload, GetBillingPortalPayload } from "../lib/schema";
import type { User } from "@akashic-labs/auth";

export interface WebhookCallbacks {
  onCheckoutSessionCompleted?: (sessionId: string) => Promise<void> | void;
  onSubscriptionCreated?: (subscriptionId: string) => Promise<void> | void;
  onSubscriptionUpdated?: (subscriptionId: string) => Promise<void> | void;
  onSubscriptionDeleted?: (subscriptionId: string) => Promise<void> | void;
  onEvent?: (event: unknown) => Promise<void> | void;
}

export interface BillingProviderStrategy {
  webhookHandler: (
    req: Request,
    callbacks?: WebhookCallbacks,
  ) => Promise<Response>;
  checkout: (
    input: CheckoutPayload & { user: User },
  ) => Promise<{ url: string | null }>;
  getBillingPortal: (
    input: GetBillingPortalPayload & { user: User },
  ) => Promise<{ url: string }>;
}
