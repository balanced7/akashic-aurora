import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { handle } from "@akashic-labs/api/utils";
import { env } from "@akashic-labs/billing/env";

import { api } from "~/lib/api/server";
import { getSession } from "~/lib/auth/server";
import { getQueryClient } from "~/lib/query/server";
import { billing } from "~/modules/billing/lib/api";

import { PricingSection } from "./section";

export const Pricing = async () => {
  const { user } = await getSession();

  const queryClient = getQueryClient();

  if (user) {
    await queryClient.prefetchQuery({
      ...billing.queries.customer.get,
      queryFn: handle(api.billing.customer.$get),
    });
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <PricingSection user={user} model={env.BILLING_MODEL} />
    </HydrationBoundary>
  );
};
