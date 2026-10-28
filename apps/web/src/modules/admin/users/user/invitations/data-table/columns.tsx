import dayjs from "dayjs";

import { InvitationStatus, MemberRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import {
  Avatar,
  AvatarImage,
  AvatarFallback,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";

import { pathsConfig } from "~/config/paths";
import { InvitationActions } from "~/modules/admin/organizations/organization/invitations/data-table/columns";
import { TurboLink } from "~/modules/common/turbo-link";

import type { GetUserInvitationsResponse } from "@akashic-labs/api/schema";
import type { ColumnDef } from "@tanstack/react-table";

export const useColumns = (): ColumnDef<
  GetUserInvitationsResponse["data"][number]
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
              row.original.organization.id,
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
      id: "status",
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("status")} />
      ),
      cell: ({ row }) => {
        return <Badge variant="secondary">{t(row.original.status)}</Badge>;
      },
      meta: {
        label: t("status"),
        variant: "multiSelect",
        options: Object.values(InvitationStatus).map((status) => ({
          label: t(status),
          value: status,
        })),
      },
      enableColumnFilter: true,
    },
    {
      id: "expiresAt",
      accessorKey: "expiresAt",
      header: ({ column }) => (
        <div className="ml-auto w-fit">
          <DataTableColumnHeader column={column} title={t("expiresAt")} />
        </div>
      ),
      cell: ({ row }) => {
        return (
          <div
            className={cn("ml-auto text-right", {
              "text-destructive": dayjs(row.original.expiresAt).isBefore(
                dayjs(),
              ),
            })}
          >
            {new Date(row.original.expiresAt).toLocaleString(i18n.language, {
              hour: "2-digit",
              minute: "2-digit",
              year: "numeric",
              month: "numeric",
              day: "2-digit",
            })}
          </div>
        );
      },
      meta: {
        label: t("expiresAt"),
        variant: "dateRange",
      },
      enableColumnFilter: true,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="ml-auto w-fit">
          <InvitationActions invitation={row.original} />
        </div>
      ),
      enableHiding: false,
    },
  ];
};
