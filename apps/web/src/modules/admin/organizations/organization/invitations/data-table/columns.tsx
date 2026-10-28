import { useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { toast } from "sonner";

import { InvitationStatus, MemberRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Avatar, AvatarFallback } from "@akashic-labs/ui-web/avatar";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button } from "@akashic-labs/ui-web/button";
import { DataTableColumnHeader } from "@akashic-labs/ui-web/data-table/data-table-column-header";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@akashic-labs/ui-web/dropdown-menu";
import { Icons } from "@akashic-labs/ui-web/icons";

import { admin } from "~/modules/admin/lib/api";

import type { Invitation } from "@akashic-labs/auth";
import type { ColumnDef } from "@tanstack/react-table";

export const InvitationActions = ({
  invitation,
}: {
  invitation: Invitation;
}) => {
  const { t } = useTranslation(["common", "organization"]);
  const queryClient = useQueryClient();

  const cancelInvitation = useMutation({
    ...admin.mutations.organizations.invitations.delete,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.organizations.getInvitations({
          id: invitation.organizationId,
        }),
      );
      toast.success(t("invitations.cancel.success"));
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
        {(() => {
          const isPending =
            cancelInvitation.isPending &&
            cancelInvitation.variables.invitationId === invitation.id;

          return (
            <DropdownMenuItem
              variant="destructive"
              onClick={() =>
                cancelInvitation.mutate({
                  id: invitation.organizationId,
                  invitationId: invitation.id,
                })
              }
              disabled={isPending}
              key={`cancel-${invitation.id}`}
            >
              {t("cancel")}
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

export const useColumns = (): ColumnDef<Invitation>[] => {
  const { t, i18n } = useTranslation("common");

  return [
    {
      id: "email",
      accessorKey: "email",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("email")} />
      ),
      cell: ({ row }) => {
        return (
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback>
                <Icons.UserRound className="w-4" />
              </AvatarFallback>
            </Avatar>
            <span className="truncate font-medium">{row.original.email}</span>
          </div>
        );
      },
      enableHiding: false,
      meta: {
        placeholder: `${t("search")}...`,
        variant: "text",
      },
      enableColumnFilter: true,
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
