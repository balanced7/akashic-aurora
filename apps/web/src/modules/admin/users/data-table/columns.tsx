import { UserRole } from "@akashic-labs/auth";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { TurboLink } from "~/modules/common/turbo-link";

import type { User } from "@akashic-labs/auth";
import type { ColumnDef } from "@tanstack/react-table";

export const useColumns = (): ColumnDef<User>[] => {
  const { t, i18n } = useTranslation("common");
  const { data: session } = authClient.useSession();

  return [
    {
      id: "q",
      accessorKey: "q",
      meta: {
        placeholder: `${t("search")}...`,
        variant: "text",
      },
      enableHiding: false,
      enableColumnFilter: true,
    },
    {
      id: "name",
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("name")} />
      ),
      cell: ({ row }) => {
        return (
          <TurboLink
            href={pathsConfig.admin.users.user(row.original.id)}
            className="group flex items-center gap-3"
          >
            <Avatar>
              <AvatarImage
                src={row.original.image ?? undefined}
                alt={row.original.name}
              />
              <AvatarFallback>
                <Icons.UserRound className="w-5" />
              </AvatarFallback>
            </Avatar>
            <div className="flex items-center gap-2">
              <span className="group-hover:text-primary truncate font-medium underline underline-offset-4">
                {row.original.name}
              </span>
              {row.original.id === session?.user.id && (
                <Badge variant="outline">{t("you")}</Badge>
              )}
            </div>
          </TurboLink>
        );
      },
      enableHiding: false,
    },
    {
      id: "email",
      accessorKey: "email",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("email")} />
      ),
      cell: ({ row }) => {
        return (
          <div className="flex items-center gap-2">
            {row.original.email}

            <Badge
              className={cn({
                "bg-success/15 text-success hover:bg-success/25":
                  row.original.emailVerified,
                "bg-destructive/15 text-destructive hover:bg-destructive/25":
                  !row.original.emailVerified,
              })}
            >
              {row.original.emailVerified ? t("verified") : t("unverified")}
            </Badge>
          </div>
        );
      },
      meta: {
        label: t("email"),
      },
    },
    {
      id: "role",
      accessorKey: "role",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("role")} />
      ),
      cell: ({ row }) => {
        if (!row.original.role) {
          return <Badge variant="outline">{t(UserRole.USER)}</Badge>;
        }

        return (
          <div className="flex items-center gap-1">
            {row.original.role.split(",").map((role) => (
              <Badge variant="outline" key={role}>
                {isKey(role, i18n, "common") ? t(role) : role}
              </Badge>
            ))}
          </div>
        );
      },
      meta: {
        label: t("role"),
        variant: "multiSelect",
        options: Object.values(UserRole).map((role) => ({
          label: t(role),
          value: role,
        })),
      },
      enableColumnFilter: true,
    },
    {
      id: "twoFactorEnabled",
      accessorKey: "twoFactorEnabled",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={"2FA"} />
      ),
      cell: ({ row }) => {
        return row.original.twoFactorEnabled ? (
          <>
            <span className="sr-only">{t("enabled")}</span>
            <Icons.Check className="size-4" />
          </>
        ) : (
          <>
            <span className="sr-only">{t("disabled")}</span>
            <Icons.X className="size-4" />
          </>
        );
      },
      meta: {
        label: "2FA",
        variant: "multiSelect",
        options: [
          { label: t("enabled"), value: "true" },
          { label: t("disabled"), value: "false" },
        ],
      },
      enableColumnFilter: true,
    },
    {
      id: "banned",
      accessorKey: "banned",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("banned")} />
      ),
      cell: ({ row }) => {
        return row.original.banned ? (
          <>
            <span className="sr-only">{t("banned")}</span>
            <Icons.Check className="size-4" />
          </>
        ) : (
          <>
            <span className="sr-only">{t("notBanned")}</span>
            <Icons.X className="size-4" />
          </>
        );
      },
      meta: {
        label: t("banned"),
        variant: "multiSelect",
        options: [
          { label: t("banned"), value: "true" },
          { label: t("notBanned"), value: "false" },
        ],
      },
      enableColumnFilter: true,
    },
    {
      id: "createdAt",
      accessorKey: "createdAt",
      header: ({ column }) => (
        <div className="ml-auto w-fit">
          <DataTableColumnHeader column={column} title={t("createdAt")} />
        </div>
      ),
      cell: ({ row }) => {
        return (
          <div className="ml-auto text-right">
            {row.original.createdAt.toLocaleDateString(i18n.language)}
          </div>
        );
      },
      meta: {
        label: t("createdAt"),
        variant: "dateRange",
      },
      enableColumnFilter: true,
    },
  ];
};
