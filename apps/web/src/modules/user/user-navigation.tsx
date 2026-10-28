"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { memo } from "react";

import { hasAdminPermission } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuPortal,
  DropdownMenuGroup,
} from "@akashic-labs/ui-web/dropdown-menu";
import { Icons } from "@akashic-labs/ui-web/icons";
import { SidebarMenuButton, useSidebar } from "@akashic-labs/ui-web/sidebar";
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { auth } from "~/modules/auth/lib/api";
import { ThemeControlsProvider } from "~/modules/common/theme";
import { TurboLink } from "~/modules/common/turbo-link";

import type { User } from "@akashic-labs/auth";

interface UserNavigationProps {
  readonly user: User;
}

export const UserNavigation = memo<UserNavigationProps>(({ user }) => {
  const { t } = useTranslation(["common", "auth"]);
  const router = useRouter();
  const { isMobile, setOpenMobile } = useSidebar();
  const { refetch } = authClient.useListOrganizations();

  const signOut = useMutation({
    ...auth.mutations.signOut,
    onSuccess: async () => {
      await refetch();
      router.replace(pathsConfig.index);
      router.refresh();
    },
  });

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
        >
          <Avatar className="size-8 bg-white/10 backdrop-blur-md backdrop-saturate-150 dark:bg-black/10">
            <AvatarImage src={user.image ?? undefined} alt={user.name} />
            <AvatarFallback className="border-0 bg-transparent">
              <Icons.UserRound className="w-5" />
            </AvatarFallback>
          </Avatar>

          <div className="grid flex-1 text-left text-sm leading-tight">
            {user.name && (
              <span className="truncate font-medium">{user.name}</span>
            )}
            {user.email && (
              <span className="truncate text-xs">{user.email}</span>
            )}
          </div>
          <Icons.EllipsisVertical className="ml-auto size-4" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>

      <DropdownMenuPortal>
        <DropdownMenuContent
          className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
          side={isMobile ? "bottom" : "right"}
          align="end"
          sideOffset={4}
        >
          <DropdownMenuLabel className="flex items-center gap-2 font-normal">
            <Avatar className="size-8 bg-white/10 backdrop-blur-md backdrop-saturate-150 dark:bg-black/10">
              <AvatarImage src={user.image ?? undefined} alt={user.name} />
              <AvatarFallback className="border-0 bg-transparent">
                <Icons.UserRound className="w-5" />
              </AvatarFallback>
            </Avatar>

            <div className="flex w-full min-w-0 flex-col space-y-1">
              {user.name && (
                <p className="truncate text-sm leading-none font-medium">
                  {user.name}
                </p>
              )}
              {user.email && (
                <p className="text-muted-foreground truncate text-xs leading-none">
                  {user.email}
                </p>
              )}
            </div>
          </DropdownMenuLabel>

          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem asChild>
              <TurboLink
                href={pathsConfig.dashboard.user.index}
                className="flex w-full cursor-pointer items-center gap-1.5"
                onClick={() => setOpenMobile(false)}
              >
                <Icons.Home className="size-4" />
                {t("dashboard")}
              </TurboLink>
            </DropdownMenuItem>

            <DropdownMenuItem asChild>
              <TurboLink
                href={pathsConfig.dashboard.user.settings.index}
                className="flex w-full cursor-pointer items-center gap-1.5"
                onClick={() => setOpenMobile(false)}
              >
                <Icons.Settings className="size-4" />
                {t("settings")}
              </TurboLink>
            </DropdownMenuItem>
          </DropdownMenuGroup>

          <DropdownMenuSeparator />

          <DropdownMenuGroup>
            <ThemeControlsProvider>
              <DropdownMenuItem asChild onSelect={(e) => e.preventDefault()}>
                <div className="flex w-full cursor-pointer items-center gap-1.5">
                  <Icons.Sun className="size-4 dark:hidden" />
                  <Icons.Moon className="hidden size-4 dark:block" />
                  {t("theme.title")}

                  <div className="bg-primary ml-auto size-3 rounded-full"></div>
                </div>
              </DropdownMenuItem>
            </ThemeControlsProvider>
          </DropdownMenuGroup>

          {hasAdminPermission(user) && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <TurboLink
                  href={pathsConfig.admin.index}
                  className="flex w-full cursor-pointer items-center gap-1.5"
                >
                  <Icons.ShieldUser className="size-4" />
                  {t("common:admin")}
                </TurboLink>
              </DropdownMenuItem>
            </>
          )}

          <DropdownMenuSeparator />

          <DropdownMenuItem asChild className="cursor-pointer">
            <button
              className="flex w-full items-center gap-1.5"
              onClick={() => signOut.mutate(undefined)}
            >
              <Icons.LogOut className="size-4" />
              {t("logout.cta")}
            </button>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenu>
  );
});

export const UserNavigationSkeleton = () => {
  return <Skeleton className="size-10 rounded-full" />;
};

UserNavigation.displayName = "UserNavigation";
