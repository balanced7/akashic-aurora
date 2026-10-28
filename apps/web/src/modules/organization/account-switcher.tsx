"use client";

import { useRouter } from "next/navigation";
import { memo, useState } from "react";

import { PricingPlanType } from "@akashic-labs/billing";
import { useTranslation } from "@akashic-labs/i18n";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import {
  Command,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@akashic-labs/ui-web/command";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverPortal,
} from "@akashic-labs/ui-web/popover";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { useCustomer } from "~/modules/billing/hooks/use-customer";
import { TurboLink } from "~/modules/common/turbo-link";
import { CreateOrganizationModal } from "~/modules/organization/create-organization";

import { useActiveOrganization } from "./hooks/use-active-organization";

import type { User } from "@akashic-labs/auth";

interface AccountSwitcherProps {
  readonly user: User;
}

export const AccountSwitcher = memo<AccountSwitcherProps>(({ user }) => {
  const { t } = useTranslation(["common", "auth", "organization"]);
  const { isMobile } = useSidebar();
  const router = useRouter();

  const [open, setOpen] = useState(false);
  const [createOrganizationOpen, setCreateOrganizationOpen] = useState(false);

  const { data: customer } = useCustomer();
  const { data: organizations } = authClient.useListOrganizations();
  const { activeOrganization } = useActiveOrganization();

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <Popover open={open} onOpenChange={setOpen} modal>
          <PopoverTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="size-8 bg-white/10 backdrop-blur-md backdrop-saturate-150 dark:bg-black/10">
                {activeOrganization ? (
                  <>
                    <AvatarImage
                      src={activeOrganization.logo ?? undefined}
                      alt={activeOrganization.name}
                    />
                    <AvatarFallback className="border-0 bg-transparent">
                      <span className="text-muted-foreground text-sm uppercase">
                        {activeOrganization.name.charAt(0)}
                      </span>
                    </AvatarFallback>
                  </>
                ) : (
                  <>
                    <AvatarImage
                      src={user.image ?? undefined}
                      alt={user.name}
                    />
                    <AvatarFallback className="border-0 bg-transparent">
                      <Icons.UserRound className="w-5" />
                    </AvatarFallback>
                  </>
                )}
              </Avatar>

              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">
                  {activeOrganization
                    ? activeOrganization.name
                    : t("account.personal")}
                </span>
                <span className="truncate text-xs capitalize">
                  {(customer?.plan ?? PricingPlanType.FREE).toLowerCase()}
                </span>
              </div>

              <Icons.ChevronsUpDown className="ml-auto" />
            </SidebarMenuButton>
          </PopoverTrigger>

          <PopoverPortal>
            <PopoverContent
              className="w-(--radix-popover-trigger-width) min-w-60 rounded-lg p-0"
              align="start"
              side={isMobile ? "bottom" : "right"}
              sideOffset={4}
            >
              <Command
                defaultValue={activeOrganization?.slug ?? "personal-account"}
              >
                <CommandInput placeholder={t("search")} autoFocus />
                <CommandList>
                  <CommandGroup>
                    <CommandItem
                      value="personal-account"
                      className="p-2"
                      onSelect={() => {
                        setOpen(false);
                        router.replace(pathsConfig.dashboard.user.index);
                      }}
                      asChild
                    >
                      <TurboLink href={pathsConfig.dashboard.user.index}>
                        <Avatar className="size-6">
                          <AvatarImage
                            src={user.image ?? undefined}
                            alt={user.name}
                          />
                          <AvatarFallback>
                            <Icons.UserRound className="size-3.5" />
                          </AvatarFallback>
                        </Avatar>
                        {t("account.personal")}

                        {!activeOrganization && (
                          <Icons.Check className="ml-auto" />
                        )}
                      </TurboLink>
                    </CommandItem>
                  </CommandGroup>
                  <CommandSeparator />
                  {organizations && organizations.length > 0 && (
                    <>
                      <CommandGroup
                        heading={`${t("organizations")} (${organizations.length})`}
                      >
                        {organizations.map((organization) => (
                          <CommandItem
                            value={organization.slug}
                            key={organization.id}
                            className="p-2"
                            asChild
                            onSelect={() => {
                              router.replace(
                                pathsConfig.dashboard.organization(
                                  organization.slug,
                                ).index,
                              );
                            }}
                          >
                            <TurboLink
                              href={
                                pathsConfig.dashboard.organization(
                                  organization.slug,
                                ).index
                              }
                              className="leading-tight"
                            >
                              <Avatar className="size-6">
                                <AvatarImage
                                  src={organization.logo ?? undefined}
                                  alt={organization.name}
                                />
                                <AvatarFallback>
                                  <span className="text-muted-foreground text-sm uppercase">
                                    {organization.name.charAt(0)}
                                  </span>
                                </AvatarFallback>
                              </Avatar>
                              {organization.name}

                              {activeOrganization?.slug ===
                                organization.slug && (
                                <Icons.Check className="ml-auto" />
                              )}
                            </TurboLink>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                      <CommandSeparator />
                    </>
                  )}

                  <CommandGroup forceMount>
                    <CommandItem
                      className="p-2"
                      onSelect={() => setCreateOrganizationOpen(true)}
                    >
                      <div className="flex size-6 items-center justify-center rounded-md border bg-transparent">
                        <Icons.Plus className="size-4" />
                      </div>
                      {t("create.cta")}
                    </CommandItem>
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </PopoverPortal>
        </Popover>

        <CreateOrganizationModal
          open={createOrganizationOpen}
          onOpenChange={setCreateOrganizationOpen}
        />
      </SidebarMenuItem>
    </SidebarMenu>
  );
});

AccountSwitcher.displayName = "AccountSwitcher";
