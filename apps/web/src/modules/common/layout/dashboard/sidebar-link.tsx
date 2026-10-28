"use client";

import { useParams, usePathname } from "next/navigation";
import { memo } from "react";

import { cn } from "@akashic-labs/ui";
import { SidebarMenuButton, useSidebar } from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";

import type { ComponentProps } from "react";

interface SidebarLinkProps extends ComponentProps<typeof SidebarMenuButton> {
  href: string;
}

export const SidebarLink = memo<SidebarLinkProps>(
  ({ href, children, ...props }) => {
    const { setOpenMobile } = useSidebar();

    const pathname = usePathname();
    const params = useParams();

    const normalizedPathname = pathname.replace(
      `/${params.locale?.toString()}`,
      "",
    );

    return (
      <SidebarMenuButton
        asChild
        isActive={
          [
            pathsConfig.admin.index,
            pathsConfig.dashboard.user.index,
            ...(params.organization
              ? [
                  pathsConfig.dashboard.organization(
                    params.organization.toString(),
                  ).index,
                ]
              : []),
          ].includes(href)
            ? normalizedPathname === href
            : normalizedPathname.startsWith(href)
        }
        className={cn(
          // "Glass" overlay (translucent, not plain grey)
          "bg-white/10 backdrop-blur-md backdrop-saturate-150 dark:bg-black/10",
          "hover:bg-white/50 dark:hover:bg-black/15",
          "data-[active=true]:bg-white/50 dark:data-[active=true]:bg-black/15",
          // Luminosity outline + pastel glow that plays nicely with the gradient behind it
          "relative",
          "before:pointer-events-none before:absolute before:inset-0 before:rounded-md before:opacity-80 before:[mix-blend-mode:luminosity] hover:before:border hover:before:border-white/30 data-[active=true]:before:border data-[active=true]:before:border-white/30 dark:before:border-white/10",
          "before:shadow-[0_0_0_1px_rgba(255,255,255,0.14),0_0_18px_rgba(168,85,247,0.12),0_0_26px_rgba(59,130,246,0.08)]",
          "before:transition-[opacity,box-shadow] before:duration-200",
          "hover:before:opacity-100 hover:before:shadow-[0_0_0_1px_rgba(255,255,255,0.20),0_0_22px_rgba(168,85,247,0.16),0_0_34px_rgba(59,130,246,0.12)]",
          "data-[active=true]:before:opacity-100 data-[active=true]:before:shadow-[0_0_0_1px_rgba(255,255,255,0.24),0_0_28px_rgba(168,85,247,0.20),0_0_44px_rgba(59,130,246,0.14)]",
          props.className,
        )}
        {...props}
      >
        <TurboLink href={href} onClick={() => setOpenMobile(false)}>
          {children}
        </TurboLink>
      </SidebarMenuButton>
    );
  },
);
