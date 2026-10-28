import { notFound, redirect } from "next/navigation";

import { handle } from "@akashic-labs/api/utils";

import { pathsConfig } from "~/config/paths";
import { api } from "~/lib/api/server";
import { getInvitation, getSession } from "~/lib/auth/server";
import { getMetadata } from "~/lib/metadata";
import { Invitation } from "~/modules/organization/invitations/invitation";
import { InvitationEmailMismatch } from "~/modules/organization/invitations/invitation-email-mismatch";
import { InvitationExpired } from "~/modules/organization/invitations/invitation-expired";

export const generateMetadata = getMetadata({
  title: "organization:join.title",
  description: "organization:join.description",
});

export default async function JoinPage({
  searchParams,
}: {
  searchParams: Promise<{ invitationId?: string; email?: string }>;
}) {
  const { invitationId, email } = await searchParams;

  if (!invitationId) {
    return notFound();
  }

  const { user } = await getSession();

  if (!user) {
    const searchParams = new URLSearchParams();
    searchParams.set("invitationId", invitationId);
    if (email) searchParams.set("email", email);
    searchParams.set(
      "redirectTo",
      `${pathsConfig.auth.join}?${searchParams.toString()}`,
    );
    return redirect(`${pathsConfig.auth.login}?${searchParams.toString()}`);
  }

  const invitation = await getInvitation({ id: invitationId });

  if (invitation) {
    const { organization } = await handle(api.organizations[":id"].$get)({
      param: {
        id: invitation.organizationId,
      },
    });

    if (!organization) {
      return notFound();
    }

    return <Invitation invitation={invitation} organization={organization} />;
  }

  if (email && user.email !== email) {
    return (
      <InvitationEmailMismatch invitationId={invitationId} email={email} />
    );
  }

  return <InvitationExpired />;
}
