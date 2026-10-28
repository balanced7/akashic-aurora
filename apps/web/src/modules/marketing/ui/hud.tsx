import { cn } from "@akashic-labs/ui";

import { statusLabel } from "~/modules/marketing/content/aurora";

import type { ComponentProps, ReactNode } from "react";
import type { FeatureStatus } from "~/modules/marketing/content/aurora";

/**
 * HUD highlight layer. These pieces are the 10% accent on a Framer-style canvas.
 * Use them for the few moments we want the eye to land on.
 */

interface HudFrameProps extends ComponentProps<"div"> {
  readonly tone?: "gold" | "cyan";
  readonly scan?: boolean;
}

export const HudFrame = ({
  tone = "gold",
  scan,
  className,
  children,
  ...props
}: HudFrameProps) => (
  <div
    {...props}
    className={cn("hud-frame", tone === "cyan" && "hud-frame-cyan", className)}
  >
    {scan && (
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <span
          className={cn(
            "animate-hud-scan absolute inset-x-0 h-1/3 bg-gradient-to-b from-transparent to-transparent",
            tone === "gold" ? "via-hud-gold/10" : "via-hud-cyan/10",
          )}
        />
      </span>
    )}
    {children}
  </div>
);

export const HudLabel = ({
  children,
  tone = "gold",
  className,
}: {
  children: ReactNode;
  tone?: "gold" | "cyan" | "muted";
  className?: string;
}) => (
  <span
    className={cn(
      "hud-label text-[11px]",
      tone === "gold" && "text-hud-gold",
      tone === "cyan" && "text-hud-cyan",
      tone === "muted" && "text-mk-faint",
      className,
    )}
  >
    {children}
  </span>
);

/** Eyebrow with the hextech gem: the strongest highlight marker */
export const HudBadge = ({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) => (
  <span
    className={cn(
      "hud-corners text-hud-gold-bright relative inline-flex items-center gap-2.5 px-3.5 py-1.5",
      className,
    )}
  >
    <span className="hud-gem" />
    <span className="hud-label text-[11px]">{children}</span>
  </span>
);

export const HudStat = ({
  value,
  label,
  note,
  tone = "gold",
}: {
  value: ReactNode;
  label: ReactNode;
  note?: ReactNode;
  tone?: "gold" | "cyan";
}) => (
  <div className="flex flex-col gap-1.5">
    <span
      className={cn(
        "font-hud text-4xl font-semibold tracking-tight tabular-nums sm:text-5xl",
        tone === "gold"
          ? "text-hud-gold-bright hud-glow-gold"
          : "text-hud-cyan hud-glow-cyan",
      )}
    >
      {value}
    </span>
    <HudLabel tone="muted">{label}</HudLabel>
    {note && <span className="text-mk-faint text-xs">{note}</span>}
  </div>
);

export const HudDivider = ({ className }: { className?: string }) => (
  <div aria-hidden className={cn("flex items-center gap-3", className)}>
    <span className="via-hud-gold/60 h-px flex-1 bg-gradient-to-r from-transparent to-transparent" />
    <span className="hud-gem" />
    <span className="via-hud-gold/60 h-px flex-1 bg-gradient-to-r from-transparent to-transparent" />
  </div>
);

const statusStyles: Record<FeatureStatus, string> = {
  live: "text-hud-cyan border-hud-cyan/30 bg-hud-cyan/[0.08]",
  "opt-in": "text-hud-gold border-hud-gold/30 bg-hud-gold/[0.08]",
  partial: "text-mk-muted border-white/15 bg-white/[0.04]",
  planned: "text-mk-faint border-white/10 bg-transparent border-dashed",
};

export const StatusTag = ({ status }: { status: FeatureStatus }) => (
  <span
    className={cn(
      "font-hud inline-flex h-5 items-center rounded-sm border px-1.5 text-[10px] font-semibold tracking-[0.12em] uppercase",
      statusStyles[status],
    )}
  >
    {statusLabel[status]}
  </span>
);
