"use client";

import { ChevronDown, Github, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { cn } from "@akashic-labs/ui";

import {
  links,
  navGroups,
  navLinks,
  routes,
} from "~/modules/marketing/content/site";
import { SearchTrigger } from "~/modules/marketing/layout/command-palette";
import { AkashicWordmark, NavIconGlyph } from "~/modules/marketing/ui/brand";
import { ButtonLink } from "~/modules/marketing/ui/primitives";

import type { NavGroup } from "~/modules/marketing/content/site";

export const SiteHeader = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const pathname = usePathname();
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpenGroup(null);
    setIsMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = isMobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileOpen]);

  const open = (label: string) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpenGroup(label);
  };
  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setOpenGroup(null), 120);
  };

  return (
    <header
      data-testid="site-header"
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300",
        isScrolled || openGroup || isMobileOpen
          ? "border-b border-white/[0.06] bg-black/80 backdrop-blur-xl"
          : "border-b border-transparent",
      )}
      onKeyDown={(event) => event.key === "Escape" && setOpenGroup(null)}
    >
      <div className="mk-container flex h-16 items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          <Link
            href={routes.home}
            aria-label="Akashic Labs home"
            className="shrink-0"
          >
            <AkashicWordmark />
          </Link>

          <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
            {navGroups.map((group) => (
              <div
                key={group.label}
                className="relative"
                onMouseEnter={() => open(group.label)}
                onMouseLeave={scheduleClose}
              >
                <button
                  type="button"
                  aria-expanded={openGroup === group.label}
                  aria-haspopup="true"
                  onClick={() =>
                    openGroup === group.label
                      ? setOpenGroup(null)
                      : open(group.label)
                  }
                  className={cn(
                    "flex h-9 items-center gap-1 rounded-lg px-3 text-[14px] font-medium transition-colors",
                    openGroup === group.label ||
                      group.items.some((item) => pathname.startsWith(item.href))
                      ? "text-white"
                      : "text-white/70 hover:text-white",
                  )}
                >
                  {group.label}
                  <ChevronDown
                    className={cn(
                      "size-3.5 transition-transform",
                      openGroup === group.label && "rotate-180",
                    )}
                  />
                </button>
                {openGroup === group.label && <MegaMenu group={group} />}
              </div>
            ))}
            {navLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex h-9 items-center rounded-lg px-3 text-[14px] font-medium transition-colors",
                  pathname.endsWith(item.href)
                    ? "text-white"
                    : "text-white/70 hover:text-white",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <SearchTrigger />
          <a
            href={links.repo}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium text-white/70 transition-colors hover:text-white sm:flex"
          >
            <Github className="size-4" />
            GitHub
          </a>
          <ButtonLink
            href={routes.docs}
            variant="secondary"
            size="sm"
            className="hidden sm:inline-flex"
          >
            Docs
          </ButtonLink>
          <ButtonLink
            href={links.doc("quickstart")}
            size="sm"
            className="hidden sm:inline-flex"
          >
            Get started
          </ButtonLink>
          <button
            type="button"
            className="flex size-9 items-center justify-center rounded-lg text-white lg:hidden"
            aria-label={isMobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMobileOpen}
            onClick={() => setIsMobileOpen((value) => !value)}
          >
            {isMobileOpen ? (
              <X className="size-5" />
            ) : (
              <Menu className="size-5" />
            )}
          </button>
        </div>
      </div>

      {isMobileOpen && <MobileMenu />}
    </header>
  );
};

const MegaMenu = ({ group }: { group: NavGroup }) => (
  <div className="absolute top-full left-0 pt-3">
    <div
      className={cn(
        "grid gap-2 rounded-2xl border border-white/[0.08] bg-[#0b0b0d]/95 p-2 shadow-[0_30px_80px_-20px_rgb(0_0_0/0.9)] backdrop-blur-xl",
        group.featured
          ? "w-[760px] grid-cols-[1fr_1.6fr]"
          : "w-[520px] grid-cols-1",
      )}
    >
      {group.featured && (
        <Link
          href={group.featured.href}
          className="group relative flex flex-col justify-end overflow-hidden rounded-xl border border-white/[0.06] bg-[#05090d] p-5"
        >
          <span
            aria-hidden
            className="absolute -top-16 -right-10 size-56 rounded-full bg-[radial-gradient(circle,rgb(10_200_185/0.45),transparent_65%)] blur-2xl transition-transform duration-500 group-hover:scale-110"
          />
          <span
            aria-hidden
            className="absolute -bottom-20 -left-10 size-48 rounded-full bg-[radial-gradient(circle,rgb(200_170_110/0.35),transparent_65%)] blur-2xl"
          />
          <span className="hud-label text-hud-gold relative mb-16 text-[10px]">
            {group.featured.eyebrow}
          </span>
          <span className="relative text-lg font-semibold tracking-tight text-white">
            {group.featured.title}
          </span>
          <span className="text-mk-muted relative mt-1 text-[13px] leading-snug">
            {group.featured.description}
          </span>
        </Link>
      )}
      <ul
        className={cn(
          "grid gap-0.5",
          group.featured ? "grid-cols-2" : "grid-cols-2",
        )}
      >
        {group.items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className="flex gap-3 rounded-xl p-3 transition-colors hover:bg-white/[0.05]"
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/80">
                <NavIconGlyph icon={item.icon} />
              </span>
              <span className="flex flex-col">
                <span className="text-[14px] font-medium text-white">
                  {item.title}
                </span>
                <span className="text-mk-faint text-[12.5px] leading-snug">
                  {item.description}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

const MobileMenu = () => (
  <div className="h-[calc(100dvh-4rem)] overflow-y-auto border-t border-white/[0.06] bg-black lg:hidden">
    <div className="mk-container flex flex-col gap-8 py-8">
      {navGroups.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          <span className="hud-label text-mk-faint mb-2 text-[10px]">
            {group.label}
          </span>
          {group.items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 py-2 text-[17px] text-white"
            >
              <NavIconGlyph icon={item.icon} className="text-white/60" />
              {item.title}
            </Link>
          ))}
        </div>
      ))}
      <div className="flex flex-col gap-1">
        {navLinks.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="py-2 text-[17px] text-white"
          >
            {item.label}
          </Link>
        ))}
      </div>
      <div className="flex gap-2">
        <ButtonLink href={links.doc("quickstart")} size="lg" className="flex-1">
          Get started
        </ButtonLink>
        <ButtonLink
          href={links.repo}
          variant="secondary"
          size="lg"
          className="flex-1"
        >
          GitHub
        </ButtonLink>
      </div>
    </div>
  </div>
);
