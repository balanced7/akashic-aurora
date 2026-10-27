import { notFound } from "next/navigation";

import { getOrganization } from "~/lib/auth/server";
import { getMetadata } from "~/lib/metadata";
import { DeleteOrganization } from "~/modules/organization/settings/delete-organization";
import { EditLogo } from "~/modules/organization/settings/edit-logo";
import { EditName } from "~/modules/organization/settings/edit-name";
import { LeaveOrganization } from "~/modules/organization/settings/leave-organization";

export const generateMetadata = getMetadata({
  title: "organization:settings.title",
  description: "organization:settings.header.description",
});

export default async function SettingsPage({
  params,
}: {
  params: Promise<{ organization: string }>;
}) {
  const { organization } = await params;

  const activeOrganization = await getOrganization({ slug: organization });

  if (!activeOrganization) {
    return notFound();
  }

  return (
    <>
      <EditLogo organizationId={activeOrganization.id} />
      <EditName organizationId={activeOrganization.id} />
      <LeaveOrganization organizationId={activeOrganization.id} />
      <DeleteOrganization organizationId={activeOrganization.id} />
    </>
  );
}
