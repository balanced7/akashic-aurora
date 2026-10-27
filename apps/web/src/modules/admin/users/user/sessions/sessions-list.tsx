"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { admin } from "~/modules/admin/lib/api";

interface SessionsListProps {
  readonly id: string;
}

export const SessionsList = ({ id }: SessionsListProps) => {
  const { t } = useTranslation(["common", "auth", "admin"]);
  const queryClient = useQueryClient();

  const { data: sessions, isLoading } = useQuery(
    admin.queries.users.getSessions({ id }),
  );

  const revoke = useMutation({
    ...admin.mutations.users.sessions.revoke,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.users.getSessions({ id }),
      );
      toast.success(t("account.sessions.revoke.success"));
    },
  });

  const revokeAll = useMutation({
    ...admin.mutations.users.sessions.revokeAll,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.users.getSessions({ id }),
      );
      toast.success(t("users.user.sessions.revokeAll.success"));
    },
  });

  return (
    <section className="flex w-full flex-col gap-4">
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-xl font-semibold tracking-tight">
          {t("sessions")}
        </h3>

        {sessions?.sessions.length && sessions.sessions.length > 0 ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => revokeAll.mutate({ userId: id })}
            disabled={revokeAll.isPending && revokeAll.variables.userId === id}
          >
            {revokeAll.isPending && revokeAll.variables.userId === id ? (
              <Icons.Loader2 className="size-4 animate-spin" />
            ) : (
              <Icons.Trash className="size-4" />
            )}
            {t("revokeAll")}
          </Button>
        ) : null}
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : sessions?.sessions.length && sessions.sessions.length > 0 ? (
        <ul className="overflow-hidden rounded-md border">
          {sessions.sessions.map((session) => {
            return (
              <li
                key={session.id}
                className="flex min-w-0 items-center gap-3 border-b px-4 py-3 last:border-b-0"
              >
                <Icons.MonitorSmartphone className="size-6 shrink-0" />

                <div className="mr-auto grid grid-cols-1">
                  <span className="truncate text-sm font-medium capitalize">
                    {session.ipAddress}
                  </span>
                  <span className="text-muted-foreground truncate text-xs">
                    {session.userAgent}
                  </span>
                </div>

                <Button
                  variant="ghost"
                  size="icon"
                  disabled={
                    revoke.isPending &&
                    revoke.variables.sessionToken === session.token
                  }
                  onClick={() => revoke.mutate({ sessionToken: session.token })}
                  className="shrink-0"
                >
                  <span className="sr-only">
                    {t("account.sessions.revoke.cta")}
                  </span>
                  {revoke.isPending &&
                  revoke.variables.sessionToken === session.token ? (
                    <Icons.Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Icons.Trash className="size-4" />
                  )}
                </Button>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="flex items-center justify-center rounded-md border border-dashed p-14">
          <p className="text-center text-sm">
            {t("account.sessions.noSessions")}
          </p>
        </div>
      )}
    </section>
  );
};
