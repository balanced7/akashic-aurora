import { SidebarInset } from "@akashic-labs/ui-web/sidebar";

import { DashboardActionBar } from "./action-bar";

export const DashboardInset = ({ children }: { children: React.ReactNode }) => {
  return (
    <SidebarInset className="relative m-2 ml-0 rounded-xl bg-white/50 backdrop-filter-none dark:bg-black/35">
      <div className="pointer-events-none absolute inset-0 rounded-xl border border-white/30 [mix-blend-mode:luminosity] dark:border-white/5"></div>
      <DashboardActionBar />
      <div className="mx-auto flex w-full max-w-[80rem] flex-1 flex-col items-start gap-6 p-4 !pt-0 md:p-6 lg:p-7">
        {children}
      </div>
    </SidebarInset>
  );
};
