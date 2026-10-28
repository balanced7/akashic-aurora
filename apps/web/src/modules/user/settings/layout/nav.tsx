"use client";

import { useParams, usePathname } from "next/navigation";
import { memo } from "react";

import { cn } from "@akashic-labs/ui";
import { useBreakpoint } from "@akashic-labs/ui-web";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerTrigger,
} from "@akashic-labs/ui-web/drawer";
import { Icons } from "@akashic-labs/ui-web/icons";

import { TurboLink } from "~/modules/common/turbo-link";

interface SettingsNavProps {
  readonly links: {
    label: string;
    href: string;
  }[];
}

export const SettingsNav = memo(({ links }: SettingsNavProps) => {
  const isDesktop = useBreakpoint("lg");
  const pathname = usePathname();
  const params = useParams();
  const normalizedPathname = pathname.replace(
    `/${params.locale?.toString()}`,
    "",
  );

  if (isDesktop) {
    return (
      <ul className="-ml-3 flex flex-col pr-10">
        {links.map((link) => (
          <li key={link.href}>
            <TurboLink
              href={link.href}
              className={cn(
                "text-muted-foreground hover:bg-muted block rounded-md px-3 py-2.5 text-sm",
                {
                  "text-foreground font-medium":
                    normalizedPathname === link.href,
                },
              )}
            >
              {link.label}
            </TurboLink>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="outline" size="icon">
          <Icons.Menu className="size-5" />
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <ul className="flex flex-col p-6">
          {links.map((link) => (
            <li key={link.href}>
              <DrawerClose asChild>
                <TurboLink
                  href={link.href}
                  className={cn(
                    "text-muted-foreground block rounded-md py-2.5",
                    {
                      "text-foreground font-medium":
                        normalizedPathname === link.href,
                    },
                  )}
                >
                  {link.label}
                </TurboLink>
              </DrawerClose>
            </li>
          ))}
        </ul>
      </DrawerContent>
    </Drawer>
  );
});

SettingsNav.displayName = "SettingsNav";
