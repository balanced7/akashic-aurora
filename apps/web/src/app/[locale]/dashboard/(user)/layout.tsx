import { redirect } from "next/navigation";

import { Icons } from "@akashic-labs/ui-web/icons";
import { SidebarProvider } from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { getSession } from "~/lib/auth/server";
import { DashboardInset } from "~/modules/common/layout/dashboard/inset";
import { DashboardSidebar } from "~/modules/common/layout/dashboard/sidebar";

const menu = [
  {
    label: "platform",
    items: [
      {
        title: "home",
        href: pathsConfig.dashboard.user.index,
        icon: Icons.Home,
      },
      {
        title: "ai",
        href: pathsConfig.dashboard.user.ai,
        icon: Icons.Brain,
      },
      {
        title: "reports",
        href: pathsConfig.dashboard.user.reports,
        icon: Icons.BookOpen,
      },
      {
        title: "skill trees",
        href: pathsConfig.dashboard.user.skillTrees,
        icon: Icons.GraduationCap,
      },
    ],
  },
  {
    label: "account",
    items: [
      {
        title: "settings",
        href: pathsConfig.dashboard.user.settings.index,
        icon: Icons.Settings,
      },
    ],
  },
];

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user } = await getSession();

  if (!user) {
    return redirect(pathsConfig.auth.login);
  }

  return (
    <SidebarProvider className="bg-gradient-to-br from-[#E0E7FF] via-[#F3E8FF] to-[#fef3d7] transition-colors duration-300 dark:from-[#ff9f5f] dark:via-[#6c0aff] dark:via-30% dark:to-[#c03aed] dark:to-70%">
      <DashboardSidebar user={user} menu={menu} />
      <DashboardInset>{children}</DashboardInset>
    </SidebarProvider>
  );
}
