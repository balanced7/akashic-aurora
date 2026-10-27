"use client";

import { usePathname } from "next/navigation";
import { Fragment } from "react";
import * as z from "zod";

import { isKey, useTranslation } from "@akashic-labs/i18n";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@akashic-labs/ui-web/breadcrumb";
import { buttonVariants } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Separator } from "@akashic-labs/ui-web/separator";
import { SidebarTrigger } from "@akashic-labs/ui-web/sidebar";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";

const ROOT_KEY = "home";

const indexSchema = z.object({
  index: z.string(),
});

const hasIndex = (value: unknown): value is z.infer<typeof indexSchema> => {
  return indexSchema.safeParse(value).success;
};

const getDisplayKey = (rawKey: string, hasPrevious: boolean) => {
  if (rawKey === "index") return hasPrevious ? null : ROOT_KEY;
  return rawKey;
};
const isSkippedKey = (key: string) => ["user", "organization"].includes(key);

const addCrumb = (
  trail: { key: string; path?: string }[],
  rawKey: string,
  path?: string,
) => {
  const displayKey = getDisplayKey(rawKey, trail.length > 0);
  if (!displayKey || isSkippedKey(rawKey)) return trail;
  return [...trail, { key: displayKey, path }];
};

const getPath = (
  obj: unknown,
  target: string,
  current: { key: string; path?: string }[] = [],
): { key: string; path?: string }[] | null => {
  if (!obj || typeof obj !== "object") return null;

  for (const [rawKey, value] of Object.entries(
    obj as Record<string, unknown>,
  )) {
    if (typeof value === "string") {
      if (value === target) return addCrumb(current, rawKey, value);
      continue;
    }

    if (typeof value === "function") {
      const candidates = target.split("/").filter(Boolean);
      for (const candidate of candidates) {
        try {
          const result = (value as (arg: string) => unknown)(candidate);
          if (typeof result === "string") {
            if (result === target) return addCrumb(current, rawKey, result);
          } else if (result && typeof result === "object") {
            const parentPath = addCrumb(
              current,
              rawKey,
              hasIndex(result) ? result.index : undefined,
            );
            const found = getPath(result, target, parentPath);
            if (found) return found;
          }
        } catch {
          // Ignore callable errors and continue trying other candidates
        }
      }
      continue;
    }

    if (value && typeof value === "object") {
      const parentPath = addCrumb(
        current,
        rawKey,
        hasIndex(value) ? value.index : undefined,
      );
      const found = getPath(value, target, parentPath);
      if (found) return found;
    }
  }

  return null;
};

export const DashboardActionBar = () => {
  const { t, i18n } = useTranslation("common");
  const pathname = usePathname();

  const rawPath = getPath(pathsConfig, pathname);
  const path =
    rawPath?.length === 1 ? [{ ...rawPath[0], key: ROOT_KEY }] : rawPath;

  const last = path?.at(-1);

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-2 px-4 transition-[width,height] ease-linear md:px-6 lg:px-7">
      <div className="flex items-center gap-2 pr-4">
        <SidebarTrigger className="-ml-1" />
        {path ? (
          <>
            <Separator orientation="vertical" className="mr-2 h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                {path.length > 1 &&
                  path.slice(1, -1).map((item, index, array) => (
                    <Fragment key={item.key}>
                      <BreadcrumbItem>
                        <BreadcrumbLink asChild>
                          <TurboLink href={item.path ?? "#"}>
                            {isKey(item.key, i18n, "common")
                              ? t(item.key)
                              : item.key}
                          </TurboLink>
                        </BreadcrumbLink>
                      </BreadcrumbItem>
                      {index < array.length - 1 && <BreadcrumbSeparator />}
                    </Fragment>
                  ))}

                {last && (
                  <>
                    {path.length > 2 && <BreadcrumbSeparator />}
                    <BreadcrumbItem>
                      <BreadcrumbPage>
                        {isKey(last.key, i18n, "common")
                          ? t(last.key)
                          : last.key}
                      </BreadcrumbPage>
                    </BreadcrumbItem>
                  </>
                )}
              </BreadcrumbList>
            </Breadcrumb>
          </>
        ) : null}
      </div>

      <div className="text-muted-foreground flex items-center">
        <a
          href="https://github.com/akashic-labs"
          rel="noopener noreferrer"
          target="_blank"
          className={buttonVariants({ variant: "ghost", size: "icon" })}
        >
          <Icons.Github className="size-5" />
        </a>

        <a
          href="https://discord.gg/KjpK2uk3JP"
          rel="noopener noreferrer"
          target="_blank"
          className={buttonVariants({ variant: "ghost", size: "icon" })}
        >
          <Icons.Discord className="size-5" />
        </a>
      </div>
    </header>
  );
};
