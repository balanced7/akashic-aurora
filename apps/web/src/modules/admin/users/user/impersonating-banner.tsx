"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { admin } from "~/modules/admin/lib/api";

export const ImpersonatingBanner = () => {
  const { t } = useTranslation("common");
  const session = authClient.useSession();
  const router = useRouter();

  const userId = session.data?.user.id;
  const isImpersonating = !!session.data?.session.impersonatedBy;

  const stop = useMutation({
    ...admin.mutations.users.stopImpersonating,
    onSuccess: async () => {
      await session.refetch();
      router.replace(
        userId
          ? pathsConfig.admin.users.user(userId)
          : pathsConfig.admin.users.index,
      );
    },
  });

  useEffect(() => {
    if (isImpersonating) {
      document.body.style.setProperty("--banner-height", "2.5rem");
      document.body.style.paddingTop = "2.5rem";
    } else {
      document.body.style.setProperty("--banner-height", "0");
      document.body.style.paddingTop = "0";
    }
  }, [isImpersonating]);

  if (!isImpersonating) {
    return null;
  }

  return (
    <div className="bg-primary fixed top-0 left-0 z-50 flex h-10 w-full items-center justify-center gap-2 px-4">
      <span className="text-primary-foreground truncate text-sm">
        {t("impersonating")}{" "}
        <span className="font-medium">{session.data?.user.email}</span>
      </span>

      <Button
        variant="outline"
        onClick={() => stop.mutate()}
        disabled={stop.isPending}
        size="sm"
        className="h-6 px-2 text-xs"
      >
        {stop.isPending ? (
          <Icons.Loader2 className="size-3 animate-spin" />
        ) : (
          "End"
        )}
      </Button>
    </div>
  );
};
