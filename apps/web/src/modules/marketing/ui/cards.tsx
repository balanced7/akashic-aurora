import { ArrowRight, ArrowUpRight, BookOpen } from "lucide-react";

import { cn } from "@akashic-labs/ui";

import { links } from "~/modules/marketing/content/site";
import { SmartLink } from "~/modules/marketing/ui/primitives";

import type { ReactNode } from "react";

export const DocCard = ({
  title,
  path,
  summary,
}: {
  title: string;
  path: string;
  summary?: string;
}) => (
  <a
    href={links.doc(path)}
    target="_blank"
    rel="noopener noreferrer"
    className="mk-card mk-card-hover group flex flex-col gap-2 p-5"
  >
    <span className="flex items-center justify-between">
      <BookOpen className="size-4 text-white/50" strokeWidth={1.6} />
      <ArrowUpRight className="size-4 text-white/50 transition-colors group-hover:text-white" />
    </span>
    <span className="mt-2 text-[15.5px] font-medium text-white">{title}</span>
    {summary && (
      <span className="text-mk-muted text-[14px] leading-relaxed">
        {summary}
      </span>
    )}
    <span className="text-mk-faint mt-auto pt-2 font-mono text-[10.5px]">
      docs/{path || "index"}
    </span>
  </a>
);

export const LinkCard = ({
  href,
  eyebrow,
  title,
  description,
  className,
  children,
}: {
  href: string;
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  className?: string;
  children?: ReactNode;
}) => (
  <SmartLink
    href={href}
    className={cn(
      "mk-card mk-card-hover group flex flex-col gap-3 p-6",
      className,
    )}
  >
    {eyebrow && (
      <span className="hud-label text-mk-faint text-[10px]">{eyebrow}</span>
    )}
    {children}
    <span className="flex items-center justify-between gap-4 text-[18px] font-medium tracking-tight text-white">
      {title}
      <ArrowRight className="size-4 shrink-0 text-white/50 transition-all group-hover:translate-x-0.5 group-hover:text-white" />
    </span>
    {description && (
      <span className="text-mk-muted text-[14.5px] leading-relaxed">
        {description}
      </span>
    )}
  </SmartLink>
);

/** A quoted line from the docs, with its source path. */
export const DocQuote = ({
  quote,
  source,
  className,
}: {
  quote: string;
  source: string;
  className?: string;
}) => (
  <figure className={cn("border-hud-gold/40 border-l-2 pl-5", className)}>
    <blockquote className="text-[19px] leading-snug font-medium tracking-tight text-white sm:text-[22px]">
      &ldquo;{quote}&rdquo;
    </blockquote>
    <figcaption className="text-mk-faint mt-3 font-mono text-[11px]">
      docs/{source}
    </figcaption>
  </figure>
);
