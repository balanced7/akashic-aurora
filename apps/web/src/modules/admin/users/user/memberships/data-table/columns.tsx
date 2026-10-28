"use client";

import { MemberRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";

import { pathsConfig } from "~/config/paths";
import { MemberActions } from "~/modules/admin/organizations/organization/members/data-table/columns";
import { TurboLink } from "~/modules/common/turbo-link";

import type { GetUserMembershipsResponse } from "@akashic-labs/api/schema";
import type { ColumnDef } from "@tanstack/react-table";

export const useColumns = (): ColumnDef<
  GetUserMembershipsResponse["data"][number]
>[] => {
  const { t, i18n } = useTranslation("common");

  return [
    {
      id: "organization.name",
      accessorKey: "organization.name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("organization")} />
      ),
      cell: ({ row }) => {
        return (
          <TurboLink
            href={pathsConfig.admin.organizations.organization(
              row.original.organizationId,
            )}
            className="group flex items-center gap-3"
          >
            <Avatar>
              <AvatarImage
                src={row.original.organization.logo ?? undefined}
                alt={row.original.organization.name}
              />
              <AvatarFallback>
                <span className="text-muted-foreground text-sm uppercase">
                  {row.original.organization.name.charAt(0)}
                </span>
              </AvatarFallback>
            </Avatar>
            <span className="group-hover:text-primary truncate font-medium underline underline-offset-4">
              {row.original.organization.name}
            </span>
          </TurboLink>
        );
      },
      enableHiding: false,
    },
    {
      id: "role",
      accessorKey: "role",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("role")} />
      ),
      cell: ({ row }) => {
        return <Badge variant="outline">{t(row.original.role)}</Badge>;
      },
      meta: {
        label: t("role"),
        variant: "multiSelect",
        options: Object.values(MemberRole).map((role) => ({
          label: t(role),
          value: role,
        })),
      },
      enableColumnFilter: true,
    },
    {
      id: "createdAt",
      accessorKey: "createdAt",
      header: ({ column }) => (
        <div className="ml-auto w-fit">
          <DataTableColumnHeader column={column} title={t("joinedAt")} />
        </div>
      ),
      cell: ({ row }) => {
        return (
          <div className="ml-auto text-right">
            {new Date(row.original.createdAt).toLocaleDateString(i18n.language)}
          </div>
        );
      },
      meta: {
        label: t("joinedAt"),
        variant: "dateRange",
      },
      enableColumnFilter: true,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="ml-auto w-fit">
          <MemberActions member={row.original} />
        </div>
      ),
      enableHiding: false,
    },
  ];
};
