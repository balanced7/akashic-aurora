import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { notFound } from "next/navigation";

import { getOrganizationResponseSchema } from "@akashic-labs/api/schema";
import { handle } from "@akashic-labs/api/utils";
import { getTranslation } from "@akashic-labs/i18n/server";

import { api } from "~/lib/api/server";
import { getMetadata } from "~/lib/metadata";
import { getQueryClient } from "~/lib/query/server";
import { admin } from "~/modules/admin/lib/api";
import { OrganizationDetails } from "~/modules/admin/organizations/organization/details";
import { OrganizationHeader } from "~/modules/admin/organizations/organization/header";
import { InvitationsDataTable } from "~/modules/admin/organizations/organization/invitations/data-table/invitations-data-table";
import { MembersDataTable } from "~/modules/admin/organizations/organization/members/data-table/members-data-table";

export const generateMetadata = async ({
  params,
}: {
  params: Promise<{ id: string; locale: string }>;
}) => {
  const id = (await params).id;
  const organization = await handle(api.admin.organizations[":id"].$get, {
    schema: getOrganizationResponseSchema,
  })({
    param: { id },
  });

  if (!organization) {
    return notFound();
  }

  return getMetadata({
    title: organization.name,
  })({ params });
};

export default async function OrganizationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { t } = await getTranslation({ ns: "common" });
  const { id } = await params;

  const organization = await handle(api.admin.organizations[":id"].$get, {
    schema: getOrganizationResponseSchema,
  })({
    param: { id },
  });

  if (!organization) {
    return notFound();
  }

  const queryClient = getQueryClient();
  queryClient.setQueryData(
    admin.queries.organizations.get({ id }).queryKey,
    organization,
  );

  const sections = [
    {
      label: t("members"),
      component: <MembersDataTable organizationId={id} />,
    },
    {
      label: t("invitations"),
      component: <InvitationsDataTable organizationId={id} />,
    },
  ];

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <OrganizationHeader id={id} />
      <OrganizationDetails id={id} />
      <div className="mt-4 flex w-full flex-col gap-10">
        {sections.map(({ label, component }) => (
          <section key={label} className="flex w-full flex-col gap-4">
            <header>
              <h3 className="text-xl font-semibold tracking-tight">{label}</h3>
            </header>
            {component}
          </section>
        ))}
      </div>
    </HydrationBoundary>
  );
}
