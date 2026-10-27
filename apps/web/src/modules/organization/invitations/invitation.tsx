"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useRouter } from "next/navigation";

import { Trans, useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { AuthHeader } from "~/modules/auth/layout/header";
import { TurboLink } from "~/modules/common/turbo-link";
import { organization } from "~/modules/organization/lib/api";
import { user } from "~/modules/user/lib/api";

import { InvitationSummaryCard } from "./invitation-summary-card";

import type { Invitation as InvitationType } from "@akashic-labs/auth";

dayjs.extend(relativeTime);

interface InvitationProps {
  readonly invitation: InvitationType & {
    inviterEmail: string;
  };
  readonly organization: {
    slug: string | null;
    name: string;
    logo: string | null;
  };
}

export const Invitation = (props: InvitationProps) => {
  const { t } = useTranslation(["common", "organization"]);
  const router = useRouter();

  const queryClient = useQueryClient();
  const acceptInvitation = useMutation({
    ...organization.mutations.invitations.accept,
    onSuccess: async () => {
      await queryClient.invalidateQueries(user.queries.invitations.getAll);
      router.replace(
        pathsConfig.dashboard.organization(props.organization.slug ?? "").index,
      );
    },
  });
  const rejectInvitation = useMutation({
    ...organization.mutations.invitations.reject,
    onSuccess: async () => {
      await queryClient.invalidateQueries(user.queries.invitations.getAll);
      router.replace(pathsConfig.dashboard.user.index);
    },
  });

  return (
    <>
      <AuthHeader
        title={t("invitations.invitation.title", {
          organizationName: props.organization.name,
        })}
        description={
          <Trans
            i18nKey="invitations.invitation.description"
            ns="organization"
            values={{
              inviterEmail: props.invitation.inviterEmail,
              organizationName: props.organization.name,
            }}
            components={{ bold: <strong /> }}
          />
        }
      />

      <InvitationSummaryCard
        invitation={props.invitation}
        organization={props.organization}
      />

      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          disabled={rejectInvitation.isPending || acceptInvitation.isPending}
          onClick={() =>
            rejectInvitation.mutate({ invitationId: props.invitation.id })
          }
        >
          {rejectInvitation.isPending ? (
            <Icons.Loader2 className="animate-spin" />
          ) : (
            <Icons.X />
          )}
          {t("reject")}
        </Button>

        <Button
          onClick={() =>
            acceptInvitation.mutate({ invitationId: props.invitation.id })
          }
          disabled={rejectInvitation.isPending || acceptInvitation.isPending}
        >
          {acceptInvitation.isPending ? (
            <Icons.Loader2 className="animate-spin" />
          ) : (
            <Icons.Check />
          )}
          {t("accept")}
        </Button>
      </div>
      <TurboLink
        href={pathsConfig.dashboard.user.index}
        className="text-muted-foreground hover:text-primary self-center text-sm font-medium underline underline-offset-4"
      >
        {t("invitations.invitation.skip")}
      </TurboLink>
    </>
  );
};
