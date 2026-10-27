"use client";

import { useQuery } from "@tanstack/react-query";

import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Icons } from "@akashic-labs/ui-web/icons";

import { authClient } from "~/lib/auth/client";
import { admin } from "~/modules/admin/lib/api";
import {
  DashboardHeader,
  DashboardHeaderTitle,
  DashboardHeaderDescription,
} from "~/modules/common/layout/dashboard/header";

import { Ban } from "./actions/ban";
import { Delete } from "./actions/delete";
import { Impersonate } from "./actions/impersonate";

interface UserHeaderProps {
  readonly id: string;
}

export const UserHeader = ({ id }: UserHeaderProps) => {
  const { t } = useTranslation("common");
  const session = authClient.useSession();
  const { data: user } = useQuery(admin.queries.users.get({ id }));

  return (
    <DashboardHeader>
      <div className="flex min-w-0 items-center gap-4">
        <Avatar className="size-12">
          <AvatarImage src={user?.image ?? undefined} alt={user?.name ?? ""} />
          <AvatarFallback>
            <Icons.UserRound className="w-7" />
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <DashboardHeaderTitle className="truncate">
              {user?.name}
            </DashboardHeaderTitle>
            {user?.isAnonymous && (
              <Badge variant="outline">{t("anonymous")}</Badge>
            )}
            {user?.id === session.data?.user.id && (
              <Badge variant="outline">{t("you")}</Badge>
            )}
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <DashboardHeaderDescription>
              {user?.email}
            </DashboardHeaderDescription>
            <Badge
              className={cn({
                "bg-success/15 text-success hover:bg-success/25":
                  user?.emailVerified,
                "bg-destructive/15 text-destructive hover:bg-destructive/25":
                  !user?.emailVerified,
              })}
            >
              {user?.emailVerified ? t("verified") : t("unverified")}
            </Badge>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Impersonate id={id} />
        <Ban id={id} />
        <Delete id={id} />
      </div>
    </DashboardHeader>
  );
};
