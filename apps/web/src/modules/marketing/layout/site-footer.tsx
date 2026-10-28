import { Github } from "lucide-react";
import Link from "next/link";

import { facts } from "~/modules/marketing/content/aurora";
import { footerColumns, links, routes } from "~/modules/marketing/content/site";
import { AkashicWordmark } from "~/modules/marketing/ui/brand";
import { SmartLink } from "~/modules/marketing/ui/primitives";

export const SiteFooter = () => (
  <footer
    data-testid="site-footer"
    className="relative border-t border-white/[0.06] bg-black pt-20 pb-10"
  >
    <div className="mk-container">
      <div className="grid gap-12 lg:grid-cols-[1.2fr_4fr]">
        <div className="flex flex-col gap-5">
          <Link href={routes.home} aria-label="Akashic Labs home">
            <AkashicWordmark />
          </Link>
          <p className="text-mk-faint max-w-xs text-sm leading-relaxed">
            Aurora is a home for your agents: shared memory, a message bus and a
            trust layer for a team of AI agents and one human.
          </p>
          <a
            href={links.repo}
            target="_blank"
            rel="noopener noreferrer"
            className="text-mk-muted inline-flex w-fit items-center gap-2 rounded-lg border border-white/[0.08] px-3 py-1.5 text-[13px] transition-colors hover:text-white"
          >
            <Github className="size-4" />
            balanced7/akashic-aurora
          </a>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-6">
          {footerColumns.map((column) => (
            <div key={column.title} className="flex flex-col gap-3">
              <span className="text-[14px] font-medium text-white">
                {column.title}
              </span>
              <ul className="flex flex-col gap-2.5">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <SmartLink
                      href={link.href}
                      className="text-mk-faint text-[14px] transition-colors hover:text-white"
                    >
                      {link.label}
                    </SmartLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-20 flex flex-col gap-4 border-t border-white/[0.06] pt-8 text-[13px] sm:flex-row sm:items-center sm:justify-between">
        <div className="text-mk-faint flex items-center gap-2">
          <span className="bg-hud-cyan size-1.5 rounded-full shadow-[0_0_8px_var(--color-hud-cyan)]" />
          Aurora is open source under {facts.license}
        </div>
        <div className="text-mk-faint flex flex-wrap items-center gap-5">
          <span>
            Press{" "}
            <kbd className="rounded border border-white/10 px-1 font-mono text-[11px]">
              ⌘K
            </kbd>{" "}
            to search
          </span>
          <a
            href="/llms.txt"
            className="font-mono text-[12px] hover:text-white"
          >
            llms.txt for agents
          </a>
          <span>© {new Date().getFullYear()} Akashic Labs</span>
        </div>
      </div>
    </div>

    <div
      aria-hidden
      className="pointer-events-none mt-16 overflow-hidden select-none"
    >
      {/* Decorative wordmark as SVG, so it reads as graphics rather than low-contrast body text. */}
      <svg
        viewBox="0 0 1000 240"
        className="mk-fade-b mx-auto block w-full max-w-[1400px]"
        role="presentation"
      >
        <defs>
          <linearGradient
            id="footer-wordmark"
            x1="0"
            y1="0"
            x2="1000"
            y2="0"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#ffffff" stopOpacity="0.03" />
            <stop offset="0.5" stopColor="#9ff5ec" stopOpacity="0.07" />
            <stop offset="1" stopColor="#c8aa6e" stopOpacity="0.04" />
          </linearGradient>
        </defs>
        <text
          x="500"
          y="215"
          textAnchor="middle"
          fontSize="270"
          fontWeight="700"
          letterSpacing="-16"
          fill="url(#footer-wordmark)"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          aurora
        </text>
      </svg>
    </div>
  </footer>
);
