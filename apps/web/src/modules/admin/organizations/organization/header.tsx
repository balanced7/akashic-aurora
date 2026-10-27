"use client";

import { useQuery } from "@tanstack/react-query";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";

import { admin } from "~/modules/admin/lib/api";
import {
  DashboardHeader,
  DashboardHeaderTitle,
  DashboardHeaderDescription,
} from "~/modules/common/layout/dashboard/header";

import { Delete } from "./actions/delete";

interface OrganizationHeaderProps {
  readonly id: string;
}

export const OrganizationHeader = ({ id }: OrganizationHeaderProps) => {
  const { data: organization } = useQuery(
    admin.queries.organizations.get({ id }),
  );

  return (
    <DashboardHeader>
      <div className="flex min-w-0 items-center gap-4">
        <Avatar className="size-12">
          <AvatarImage
            src={organization?.logo ?? undefined}
            alt={organization?.name ?? ""}
          />
          <AvatarFallback>
            <span className="text-muted-foreground text-lg uppercase">
              {organization?.name.charAt(0)}
            </span>
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <DashboardHeaderTitle className="truncate">
            {organization?.name}
          </DashboardHeaderTitle>

          <div className="flex items-center gap-2">
            <DashboardHeaderDescription>
              /{organization?.slug}
            </DashboardHeaderDescription>
          </div>
        </div>
      </div>

      <Delete id={id} />
    </DashboardHeader>
  );
};
