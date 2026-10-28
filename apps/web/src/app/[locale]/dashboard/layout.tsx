import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { redirect } from "next/navigation";

import { handle } from "@akashic-labs/api/utils";

import { pathsConfig } from "~/config/paths";
import { api } from "~/lib/api/server";
import { getSession } from "~/lib/auth/server";
import { getQueryClient } from "~/lib/query/server";
import { ImpersonatingBanner } from "~/modules/admin/users/user/impersonating-banner";
import { billing } from "~/modules/billing/lib/api";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user } = await getSession();

  if (!user) {
    return redirect(pathsConfig.auth.login);
  }

  const queryClient = getQueryClient();
  await queryClient.prefetchQuery({
    ...billing.queries.customer.get,
    queryFn: handle(api.billing.customer.$get),
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Lives here, not in the root layout, so public pages never ask for a session. */}
      <ImpersonatingBanner />
      {children}
    </HydrationBoundary>
  );
}
