import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import { useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarImage,
  AvatarFallback,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Card } from "@akashic-labs/ui-web/card";

import type { Invitation } from "@akashic-labs/auth";

interface InvitationSummaryCardProps {
  readonly invitation: Invitation;
  readonly organization: {
    slug: string | null;
    name: string;
    logo: string | null;
  };
}

dayjs.extend(relativeTime);

export const InvitationSummaryCard = ({
  invitation,
  organization,
}: InvitationSummaryCardProps) => {
  const { t } = useTranslation("common");

  return (
    <Card className="flex w-full items-center gap-4 p-4">
      <Avatar className="size-10">
        <AvatarImage
          src={organization.logo ?? undefined}
          alt={organization.name}
        />
        <AvatarFallback>
          <span className="text-muted-foreground text-xl uppercase">
            {organization.name.charAt(0)}
          </span>
        </AvatarFallback>
      </Avatar>

      <div className="flex w-full min-w-0 flex-col text-sm">
        <span className="truncate font-medium">{organization.name}</span>
        <span className="text-muted-foreground">
          {t("expires")} {dayjs(invitation.expiresAt).fromNow()}
        </span>
      </div>

      <Badge variant="outline" className="ml-auto">
        {t(invitation.role)}
      </Badge>
    </Card>
  );
};
