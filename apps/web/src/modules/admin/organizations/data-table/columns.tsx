"use client";

import { useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";

import type { GetOrganizationsResponse } from "@akashic-labs/api/schema";
import type { ColumnDef } from "@tanstack/react-table";

type Row = GetOrganizationsResponse["data"][number];

export const useColumns = (options?: {
  max?: { members: number };
}): ColumnDef<Row>[] => {
  const { t, i18n } = useTranslation("common");

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
            href={pathsConfig.admin.organizations.organization(row.original.id)}
            className="group flex items-center gap-3"
          >
            <Avatar>
              <AvatarImage
                src={row.original.logo ?? undefined}
                alt={row.original.name}
              />
              <AvatarFallback>
                <span className="text-muted-foreground text-sm uppercase">
                  {row.original.name.charAt(0)}
                </span>
              </AvatarFallback>
            </Avatar>
            <span className="group-hover:text-primary truncate font-medium underline underline-offset-4">
              {row.original.name}
            </span>
          </TurboLink>
        );
      },
      enableHiding: false,
    },
    {
      id: "slug",
      accessorKey: "slug",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("slug")} />
      ),
      cell: ({ row }) => <span>/{row.original.slug}</span>,
      meta: {
        label: "Slug",
      },
    },
    {
      id: "members",
      accessorKey: "members",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("members")} />
      ),
      cell: ({ row }) => {
        return <span>{row.original.members}</span>;
      },
      meta: {
        label: t("members"),
        variant: "range",
        range: [0, options?.max?.members ?? 100],
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
