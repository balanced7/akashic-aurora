import { cn } from "@akashic-labs/ui";

import type { CSSProperties, ReactNode } from "react";

interface RevealProps {
  readonly children: ReactNode;
  /** Stagger, in seconds, mapped onto the scroll range so later items enter a little later. */
  readonly delay?: number;
  readonly className?: string;
}

/**
 * Fade-up as the element scrolls into view, driven by CSS scroll timelines (no JavaScript).
 * Browsers without animation-timeline support, reduced motion and no-JS visitors see the content as is.
 */
export const Reveal = ({ children, delay = 0, className }: RevealProps) => (
  <div
    className={cn("mk-reveal", className)}
    style={{ "--reveal-start": `${Math.round(delay * 120)}%` } as CSSProperties}
  >
    {children}
  </div>
);
