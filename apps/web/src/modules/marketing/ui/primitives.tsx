import { ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import type { ComponentProps, ReactNode } from "react";

export const Container = ({ className, ...props }: ComponentProps<"div">) => (
  <div {...props} className={cn("mk-container", className)} />
);

export const Section = ({ className, ...props }: ComponentProps<"section">) => (
  <section
    {...props}
    className={cn("relative py-16 sm:py-20 lg:py-24", className)}
  />
);

const isExternal = (href: string) =>
  href.startsWith("http") || href.startsWith("mailto:");

interface ButtonLinkProps {
  readonly href: string;
  readonly children: ReactNode;
  readonly variant?: "primary" | "secondary" | "ghost" | "hud";
  readonly size?: "sm" | "md" | "lg";
  readonly className?: string;
  readonly arrow?: boolean;
}

const buttonVariants = {
  primary: "bg-white text-black hover:bg-white/85",
  secondary:
    "bg-white/[0.08] text-white hover:bg-white/[0.14] border border-white/[0.06]",
  ghost: "text-white hover:text-white/70 px-0",
  hud: "hud-button",
} as const;

const buttonSizes = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-5 text-[15px]",
} as const;

export const ButtonLink = ({
  href,
  children,
  variant = "primary",
  size = "md",
  className,
  arrow,
}: ButtonLinkProps) => {
  const external = isExternal(href);
  const Icon = external ? ArrowUpRight : ArrowRight;
  const classes = cn(
    "group inline-flex shrink-0 items-center justify-center gap-1.5 transition-all duration-200",
    variant === "hud"
      ? buttonVariants.hud
      : [
          buttonVariants[variant],
          buttonSizes[size],
          "rounded-lg font-medium tracking-tight",
        ],
    variant === "ghost" && "h-auto",
    className,
  );
  const content = (
    <>
      {children}
      {arrow && (
        <Icon className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
      )}
    </>
  );

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={classes}
      >
        {content}
      </a>
    );
  }

  return (
    <Link href={href} className={classes}>
      {content}
    </Link>
  );
};

export const SmartLink = ({
  href,
  children,
  className,
  ...props
}: ComponentProps<"a"> & { href: string }) => {
  if (isExternal(href)) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
        {...props}
      >
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className} {...props}>
      {children}
    </Link>
  );
};

interface SectionIntroProps {
  readonly eyebrow?: ReactNode;
  readonly title: ReactNode;
  readonly description?: ReactNode;
  readonly action?: ReactNode;
  readonly align?: "left" | "center";
  readonly className?: string;
  readonly as?: "h1" | "h2";
}

/** Framer-style header: big left-aligned title, action pinned right. */
export const SectionIntro = ({
  eyebrow,
  title,
  description,
  action,
  align = "left",
  className,
  as = "h2",
}: SectionIntroProps) => {
  const Heading = as;
  const centered = align === "center";

  return (
    <div
      className={cn(
        "flex flex-col gap-6",
        centered
          ? "items-center text-center"
          : "md:flex-row md:items-end md:justify-between",
        className,
      )}
    >
      <div
        className={cn(
          "flex max-w-3xl flex-col gap-4",
          centered && "items-center",
        )}
      >
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        <Heading
          className={cn(
            "mk-title",
            as === "h1"
              ? "text-5xl sm:text-6xl lg:text-7xl"
              : "text-4xl sm:text-5xl lg:text-[3.4rem]",
          )}
        >
          {title}
        </Heading>
        {description && (
          <p
            className={cn(
              "text-mk-muted max-w-2xl text-lg leading-relaxed text-pretty",
              centered && "mx-auto",
            )}
          >
            {description}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};

export const Eyebrow = ({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) => (
  <span
    className={cn(
      "text-mk-muted inline-flex items-center gap-2 text-sm font-medium tracking-tight",
      className,
    )}
  >
    <span className="bg-hud-cyan size-1.5 rounded-full shadow-[0_0_10px_var(--color-hud-cyan)]" />
    {children}
  </span>
);

export const Pill = ({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) => (
  <span
    className={cn(
      "text-mk-muted inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs font-medium",
      className,
    )}
  >
    {children}
  </span>
);

export const Kbd = ({ children }: { children: ReactNode }) => (
  <kbd className="text-mk-muted rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[11px]">
    {children}
  </kbd>
);

export const InlineCode = ({ children }: { children: ReactNode }) => (
  <code className="rounded-md border border-white/[0.08] bg-white/[0.05] px-1.5 py-0.5 font-mono text-[0.85em] text-white/90">
    {children}
  </code>
);
