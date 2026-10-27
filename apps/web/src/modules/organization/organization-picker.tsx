"use client";

import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Button, buttonVariants } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { TurboLink } from "~/modules/common/turbo-link";

import { CreateOrganizationModal } from "./create-organization";

export const OrganizationPicker = () => {
  const { data: organizations, isPending } = authClient.useListOrganizations();
  const { t } = useTranslation("organization");

  return (
    <nav className="@container/picker w-full">
      <ul
        className="grid grid-cols-1 gap-4 @lg/picker:grid-cols-2 @2xl/picker:grid-cols-3"
        aria-busy={isPending}
        aria-live="polite"
      >
        {isPending &&
          Array.from({ length: 2 }).map((_, index) => (
            <li key={`skeleton-${index}`} aria-hidden="true">
              <Skeleton className="h-36" />
            </li>
          ))}

        {organizations?.map((organization) => (
          <li key={organization.id}>
            <TurboLink
              className={cn(
                buttonVariants({ variant: "outline" }),
                "text-muted-foreground h-36 w-full items-center justify-between gap-3 px-6 py-4 has-[>svg]:px-6",
              )}
              href={pathsConfig.dashboard.organization(organization.slug).index}
            >
              <div className="flex w-full min-w-0 flex-col items-start gap-3">
                <Avatar className="size-16">
                  <AvatarImage src={organization.logo ?? undefined} alt="" />
                  <AvatarFallback>
                    <span className="text-muted-foreground text-xl uppercase">
                      {organization.name.charAt(0)}
                    </span>
                  </AvatarFallback>
                </Avatar>
                <span className="max-w-full truncate text-base">
                  {organization.name}
                </span>
              </div>

              <Icons.ChevronRight className="mt-2 size-4 self-start" />
            </TurboLink>
          </li>
        ))}
        <li>
          <CreateOrganizationModal>
            <Button
              type="button"
              variant="outline"
              className="text-muted-foreground h-36 w-full flex-col gap-2 border-dashed"
              aria-label={t("create.cta")}
            >
              <Icons.Plus className="size-8" strokeWidth={1.5} />
              <span className="text-base">{t("create.cta")}</span>
            </Button>
          </CreateOrganizationModal>
        </li>
      </ul>
    </nav>
  );
};
