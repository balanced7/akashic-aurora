import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { notFound } from "next/navigation";

import { getTranslation } from "@akashic-labs/i18n/server";

import { getUser } from "~/lib/auth/server";
import { getMetadata } from "~/lib/metadata";
import { getQueryClient } from "~/lib/query/server";
import { admin } from "~/modules/admin/lib/api";
import { AccountsDataTable } from "~/modules/admin/users/user/accounts/data-table/accounts-data-table";
import { UserDetails } from "~/modules/admin/users/user/details";
import { UserHeader } from "~/modules/admin/users/user/header";
import { InvitationsDataTable } from "~/modules/admin/users/user/invitations/data-table/invitations-data-table";
import { MembershipsDataTable } from "~/modules/admin/users/user/memberships/data-table/memberships-data-table";
import { PlansDataTable } from "~/modules/admin/users/user/plans/data-table/plans-data-table";
import { SessionsList } from "~/modules/admin/users/user/sessions/sessions-list";

export const generateMetadata = async ({
  params,
}: {
  params: Promise<{ id: string; locale: string }>;
}) => {
  const id = (await params).id;
  const user = await getUser({ id });

  if (!user) {
    return notFound();
  }

  return getMetadata({
    title: user.name,
  })({ params });
};

export default async function UserPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { t } = await getTranslation({ ns: "common" });
  const { id } = await params;
  const user = await getUser({ id });

  if (!user) {
    return notFound();
  }

  const queryClient = getQueryClient();
  await queryClient.setQueryData(
    admin.queries.users.get({ id }).queryKey,
    user,
  );

  const sections = [
    {
      label: t("accounts"),
      component: <AccountsDataTable id={id} />,
    },
    {
      label: t("plans"),
      component: <PlansDataTable userId={id} />,
    },
    {
      label: t("memberships"),
      component: <MembershipsDataTable userId={id} />,
    },
    {
      label: t("invitations"),
      component: <InvitationsDataTable userId={id} />,
    },
  ];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <UserHeader id={id} />
      <UserDetails id={id} />
      <div className="mt-4 flex w-full flex-col gap-10">
        {sections.map(({ label, component }) => (
          <section key={label} className="flex w-full flex-col gap-4">
            <header>
              <h3 className="text-xl font-semibold tracking-tight">{label}</h3>
            </header>
            {component}
          </section>
        ))}
        <SessionsList id={id} />
      </div>
    </HydrationBoundary>
  );
}
