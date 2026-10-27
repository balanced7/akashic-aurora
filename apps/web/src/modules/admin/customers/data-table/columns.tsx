import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { BillingStatus, config } from "@akashic-labs/billing";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button } from "@akashic-labs/ui-web/button";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@akashic-labs/ui-web/dropdown-menu";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { admin } from "~/modules/admin/lib/api";
import { TurboLink } from "~/modules/common/turbo-link";

import { invalidateCustomers } from "../server/invalidate";
import { UpdateCustomerPlanModal } from "../update-customer-plan";

import type { User } from "@akashic-labs/auth";
import type { Customer } from "@akashic-labs/billing";
import type { ColumnDef } from "@tanstack/react-table";

export const CustomerActions = ({
  customer,
}: {
  customer: Customer & { user: Pick<User, "name"> };
}) => {
  const { t } = useTranslation(["common", "admin", "billing"]);
  const queryClient = useQueryClient();

  const deleteCustomer = useMutation({
    ...admin.mutations.customers.delete,
    onSuccess: async () => {
      await invalidateCustomers();
      await queryClient.invalidateQueries(
        admin.queries.users.getPlans({
          id: customer.userId,
        }),
      );
      toast.success(t("customers.customer.delete.success"));
    },
  });

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <span className="sr-only">{t("actions")}</span>
          <Icons.Ellipsis className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        <UpdateCustomerPlanModal
          customer={customer}
          key={`update-plan-${customer.id}`}
        >
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            {t("updatePlan")}
          </DropdownMenuItem>
        </UpdateCustomerPlanModal>
        <DropdownMenuSeparator />
        {(() => {
          const isPending =
            deleteCustomer.isPending &&
            deleteCustomer.variables.id === customer.id;

          return (
            <DropdownMenuItem
              variant="destructive"
              onClick={() =>
                deleteCustomer.mutate({
                  id: customer.id,
                })
              }
              disabled={isPending}
              key={`remove-${customer.id}`}
            >
              {t("delete")}
              {isPending && (
                <Icons.Loader2 className="ml-auto animate-spin text-current" />
              )}
            </DropdownMenuItem>
          );
        })()}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export const useColumns = (): ColumnDef<
  Customer & { user: Pick<User, "name" | "image"> }
>[] => {
  const { t, i18n } = useTranslation(["common", "billing"]);
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
      id: "user.name",
      accessorKey: "user.name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("name")} />
      ),
      cell: ({ row }) => {
        return (
          <TurboLink
            href={pathsConfig.admin.users.user(row.original.userId)}
            className="group flex items-center gap-3"
          >
            <Avatar>
              <AvatarImage
                src={row.original.user.image ?? undefined}
                alt={row.original.user.name}
              />
              <AvatarFallback>
                <Icons.UserRound className="w-5" />
              </AvatarFallback>
            </Avatar>
            <div className="flex items-center gap-2">
              <span className="group-hover:text-primary truncate font-medium underline underline-offset-4">
                {row.original.user.name}
              </span>
              {row.original.userId === session?.user.id && (
                <Badge variant="outline">{t("you")}</Badge>
              )}
            </div>
          </TurboLink>
        );
      },
      enableHiding: false,
    },
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
