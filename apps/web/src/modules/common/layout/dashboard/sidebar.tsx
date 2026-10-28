import { memo } from "react";

import { isKey } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenuItem,
  SidebarRail,
} from "@akashic-labs/ui-web/sidebar";
import { SidebarMenu } from "@akashic-labs/ui-web/sidebar";
import {
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@akashic-labs/ui-web/sidebar";
import { Sidebar } from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { AccountSwitcher } from "~/modules/organization/account-switcher";
import { UserNavigation } from "~/modules/user/user-navigation";

import { SidebarLink } from "./sidebar-link";

import type { User } from "@akashic-labs/auth";
import type { Icon } from "@akashic-labs/ui-web/icons";

interface DashboardSidebarProps {
  readonly user: User;
  readonly menu: {
    label: string;
    items: {
      title: string;
      href: string;
      icon: Icon;
    }[];
  }[];
}

export const DashboardSidebar = memo<DashboardSidebarProps>(
  async ({ user, menu }) => {
    const { t, i18n } = await getTranslation({ ns: "common" });

    return (
      <Sidebar
        collapsible="icon"
        className="top-[var(--banner-height)] h-[calc(100svh-var(--banner-height))]"
      >
        <SidebarHeader>
          <AccountSwitcher user={user} />
        </SidebarHeader>
        <SidebarContent>
          {menu.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel className="uppercase">
                {isKey(group.label, i18n, "common")
                  ? t(group.label)
                  : group.label}
              </SidebarGroupLabel>
              <SidebarMenu>
                {group.items.map((item) => {
                  const title = isKey(item.title, i18n, "common")
                    ? t(item.title)
                    : item.title;
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarLink href={item.href} tooltip={title}>
                        <item.icon />
                        <span>{title}</span>
                      </SidebarLink>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroup>
          ))}

          <SidebarGroup className="mt-auto">
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarLink
                    href={pathsConfig.marketing.contact}
                    tooltip={t("support")}
                  >
                    <Icons.LifeBuoy />
                    <span>{t("support")}</span>
                  </SidebarLink>
                </SidebarMenuItem>

                <SidebarMenuItem>
                  <SidebarLink
                    href={pathsConfig.marketing.contact}
                    tooltip={t("feedback")}
                  >
                    <Icons.MessageCircle />
                    <span>{t("feedback")}</span>
                  </SidebarLink>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <UserNavigation user={user} />
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
    );
  },
);
