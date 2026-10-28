import { BillingStatus, config } from "@akashic-labs/billing";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { Badge } from "@akashic-labs/ui-web/badge";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";

import { CustomerActions } from "~/modules/admin/customers/data-table/columns";

import type { User } from "@akashic-labs/auth";
import type { Customer } from "@akashic-labs/billing";
import type { ColumnDef } from "@tanstack/react-table";

export const useColumns = (): ColumnDef<
  Customer & { user: Pick<User, "name"> }
>[] => {
  const { t, i18n } = useTranslation(["common", "billing"]);

  return [
    {
      id: "customerId",
      accessorKey: "customerId",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("id")} />
      ),
      meta: {
        label: t("id"),
      },
    },
    {
      id: "plan",
      accessorKey: "plan",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("common:plan")} />
      ),
      cell: ({ row }) => {
        const plan = config.plans.find((plan) => plan.id === row.original.plan);

        if (!plan) {
          return <span>-</span>;
        }

        return (
          <Badge variant="outline">
            {isKey(plan.name, i18n, "billing") ? t(plan.name) : plan.name}
          </Badge>
        );
      },
      meta: {
        label: t("common:plan"),
        variant: "multiSelect",
        options: Object.values(config.plans).map((plan) => ({
          label: isKey(plan.name, i18n, "billing") ? t(plan.name) : plan.name,
          value: plan.id,
        })),
      },
      enableColumnFilter: true,
    },
    {
      id: "status",
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("common:status")} />
      ),
      cell: ({ row }) => {
        const statusKey = `status.${row.original.status?.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())}`;

        if (!row.original.status) {
          return <span>-</span>;
        }

        return (
          <Badge variant="secondary">
            {isKey(statusKey, i18n, "billing") ? t(statusKey) : statusKey}
          </Badge>
        );
      },
      meta: {
        label: t("common:status"),
        variant: "multiSelect",
        options: Object.values(BillingStatus).map((status) => {
          const statusKey = `status.${status.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())}`;
          return {
            label: isKey(statusKey, i18n, "billing") ? t(statusKey) : statusKey,
            value: status,
          };
        }),
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
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="ml-auto w-fit">
          <CustomerActions customer={row.original} />
        </div>
      ),
      enableHiding: false,
    },
  ];
};
