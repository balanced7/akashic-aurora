import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { SocialProvider } from "@akashic-labs/auth";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { capitalize } from "@akashic-labs/shared/utils";
import { Button } from "@akashic-labs/ui-web/button";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuSeparator,
} from "@akashic-labs/ui-web/dropdown-menu";
import { Icons } from "@akashic-labs/ui-web/icons";

import { admin } from "~/modules/admin/lib/api";
import { SetPasswordModal } from "~/modules/admin/users/user/accounts/set-password";
import { SocialIcons } from "~/modules/auth/form/social-providers";

import type { GetUserAccountsResponse } from "@akashic-labs/api/schema";
import type { ColumnDef } from "@tanstack/react-table";

export const AccountActions = ({
  account,
}: {
  account: GetUserAccountsResponse["data"][number];
}) => {
  const { t } = useTranslation(["common", "auth", "admin"]);
  const queryClient = useQueryClient();

  const deleteAccount = useMutation({
    ...admin.mutations.users.accounts.delete,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.users.getAccounts({
          id: account.userId,
        }),
      );
      toast.success(t("users.user.accounts.delete.success"));
    },
  });

  const groups = [
    account.providerId === "credential"
      ? [
          <SetPasswordModal id={account.userId} key="set-password">
            <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
              {t("account.password.update.cta")}
            </DropdownMenuItem>
          </SetPasswordModal>,
        ]
      : null,
    [
      [
        (() => {
          const isPending =
            deleteAccount.isPending &&
            deleteAccount.variables.accountId === account.id;

          return (
            <DropdownMenuItem
              variant="destructive"
              key="delete"
              onSelect={() =>
                deleteAccount.mutate({
                  accountId: account.id,
                  id: account.userId,
                })
              }
            >
              {t("delete")}
              {isPending && (
                <Icons.Loader2 className="ml-auto animate-spin text-current" />
              )}
            </DropdownMenuItem>
          );
        })(),
      ],
    ],
  ].filter((group) => group?.filter(Boolean).length);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <span className="sr-only">{t("actions")}</span>
          <Icons.Ellipsis className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        {groups.flatMap((group, idx, array) =>
          idx < array.length - 1
            ? [group, <DropdownMenuSeparator key={`sep-${idx}`} />]
            : [group],
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export const useColumns = (): ColumnDef<
  GetUserAccountsResponse["data"][number]
>[] => {
  const { t, i18n } = useTranslation("common");

  return [
    {
      id: "providerId",
      accessorKey: "providerId",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("provider")} />
      ),
      cell: ({ row }) => {
        return (
          <div className="flex items-center gap-2">
            {row.original.providerId in SocialIcons ? (
              (() => {
                const Icon =
                  SocialIcons[row.original.providerId as SocialProvider];
                return (
                  <>
                    <Icon className="size-4" />
                    <span className="capitalize">
                      {row.original.providerId}
                    </span>
                  </>
                );
              })()
            ) : (
              <>
                <Icons.Lock className="size-4" />
                <span>{t("credential")}</span>
              </>
            )}
          </div>
        );
      },
      meta: {
        label: t("provider"),
        variant: "multiSelect",
        options: ["credential", ...Object.values(SocialProvider)].map(
          (provider) => ({
            label: isKey(provider, i18n, "common")
              ? t(provider)
              : capitalize(provider),
            value: provider,
          }),
        ),
      },
      enableColumnFilter: true,
      enableHiding: false,
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
            {new Date(row.original.createdAt).toLocaleString(i18n.language)}
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
      id: "updatedAt",
      accessorKey: "updatedAt",
      header: ({ column }) => (
        <div className="ml-auto w-fit">
          <DataTableColumnHeader column={column} title={t("updatedAt")} />
        </div>
      ),
      cell: ({ row }) => {
        return (
          <div className="ml-auto text-right">
            {new Date(row.original.createdAt).toLocaleString(i18n.language)}
          </div>
        );
      },
      meta: {
        label: t("updatedAt"),
        variant: "dateRange",
      },
      enableColumnFilter: true,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="ml-auto w-fit">
          <AccountActions account={row.original} />
        </div>
      ),
      enableHiding: false,
    },
  ];
};
