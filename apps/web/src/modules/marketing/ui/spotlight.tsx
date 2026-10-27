"use client";

import { useEffect } from "react";

/**
 * One listener for the whole page: the card under the pointer gets --spot-x/--spot-y,
 * which marketing.css turns into a soft light that follows the cursor.
 */
export const SpotlightTracker = () => {
  useEffect(() => {
    if (window.matchMedia("(hover: none)").matches) return;
    let current: HTMLElement | null = null;
    let frame = 0;

    const onMove = (event: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const target = (event.target as Element | null)?.closest<HTMLElement>(
          ".mk-card, .mk-spot",
        );
        if (current && current !== target)
          current.style.removeProperty("--spot-o");
        current = target ?? null;
        if (!current) return;
        const rect = current.getBoundingClientRect();
        current.style.setProperty("--spot-x", `${event.clientX - rect.left}px`);
        current.style.setProperty("--spot-y", `${event.clientY - rect.top}px`);
        current.style.setProperty("--spot-o", "1");
      });
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
    };
  }, []);

  return null;
};
