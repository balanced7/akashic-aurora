import { redirect } from "next/navigation";

import { hasAdminPermission } from "@akashic-labs/auth";
import { Icons } from "@akashic-labs/ui-web/icons";
import { SidebarProvider } from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { getSession } from "~/lib/auth/server";
import { AdminSidebar } from "~/modules/admin/layout/sidebar";
import { DashboardInset } from "~/modules/common/layout/dashboard/inset";

const menu = [
  {
    label: "admin",
    items: [
      {
        title: "home",
        href: pathsConfig.admin.index,
        icon: Icons.Home,
      },
      {
        title: "users",
        href: pathsConfig.admin.users.index,
        icon: Icons.UsersRound,
      },
      {
        title: "organizations",
        href: pathsConfig.admin.organizations.index,
        icon: Icons.Building,
      },
      {
        title: "customers",
        href: pathsConfig.admin.customers.index,
        icon: Icons.HandCoins,
      },
    ],
  },
];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user } = await getSession();

  if (!user) {
    return redirect(pathsConfig.auth.login);
  }

  if (!hasAdminPermission(user)) {
    return redirect(pathsConfig.dashboard.user.index);
  }

  return (
    <SidebarProvider>
      <AdminSidebar user={user} menu={menu} />
      <DashboardInset>{children}</DashboardInset>
    </SidebarProvider>
  );
}
