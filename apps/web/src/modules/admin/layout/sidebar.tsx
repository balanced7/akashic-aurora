import { memo } from "react";

import { isKey } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  SidebarGroup,
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
import { SidebarLink } from "~/modules/common/layout/dashboard/sidebar-link";
import { TurboLink } from "~/modules/common/turbo-link";
import { UserNavigation } from "~/modules/user/user-navigation";

import type { User } from "@akashic-labs/auth";
import type { Icon } from "@akashic-labs/ui-web/icons";

interface AdminSidebarProps {
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

export const AdminSidebar = memo<AdminSidebarProps>(async ({ user, menu }) => {
  const { t, i18n } = await getTranslation({ ns: "common" });

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <TurboLink
          href={pathsConfig.index}
          className="flex items-center gap-3 p-2 transition-[padding] group-data-[collapsible=icon]:p-0.5"
        >
          <Icons.Logo className="text-primary h-8 transition-[width,height]" />
          <Icons.LogoText className="text-foreground h-4 group-data-[collapsible=icon]:hidden" />
        </TurboLink>
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
});
