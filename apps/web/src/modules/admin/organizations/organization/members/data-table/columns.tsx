"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { MemberRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
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
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@akashic-labs/ui-web/dropdown-menu";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { admin } from "~/modules/admin/lib/api";
import { TurboLink } from "~/modules/common/turbo-link";

import { UpdateMemberRoleModal } from "../update-member-role";

import type { Member } from "@akashic-labs/auth";
import type { ColumnDef } from "@tanstack/react-table";

export const MemberActions = ({ member }: { member: Member }) => {
  const { t } = useTranslation(["common", "organization", "auth"]);
  const queryClient = useQueryClient();

  const removeMember = useMutation({
    ...admin.mutations.organizations.members.remove,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.organizations.getMembers({
          id: member.organizationId,
        }),
      );
      await queryClient.invalidateQueries(
        admin.queries.users.getMemberships({
          id: member.userId,
        }),
      );
      toast.success(t("members.remove.success"));
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
        <UpdateMemberRoleModal member={member} key={`update-role-${member.id}`}>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            {t("updateRole")}
          </DropdownMenuItem>
        </UpdateMemberRoleModal>
        <DropdownMenuSeparator />
        {(() => {
          const isPending =
            removeMember.isPending &&
            removeMember.variables.memberId === member.id;

          return (
            <DropdownMenuItem
              variant="destructive"
              onClick={() =>
                removeMember.mutate({
                  id: member.organizationId,
                  memberId: member.id,
                })
              }
              disabled={isPending}
              key={`remove-${member.id}`}
            >
              {t("remove")}
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

export const useColumns = (): ColumnDef<Member>[] => {
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
      id: "user.email",
      accessorKey: "user.email",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={t("email")} />
      ),
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
