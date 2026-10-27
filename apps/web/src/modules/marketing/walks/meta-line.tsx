import { cn } from "@akashic-labs/ui";

import type { ReactNode } from "react";

/**
 * "Walk 01 · Second edition · 24 min read" that wraps cleanly: each item carries its own leading
 * dot, and the list is shifted left so the dot of whichever item starts a line is clipped away.
 */
export const MetaLine = ({
  items,
  className,
}: {
  items: readonly ReactNode[];
  className?: string;
}) => (
  <div className={cn("overflow-hidden", className)}>
    <ul className="text-mk-faint -ml-5 flex flex-wrap gap-y-1 text-[13px]">
      {items.map((item, index) => (
        <li
          key={index}
          className="relative pl-5 whitespace-nowrap before:absolute before:left-2 before:content-['·']"
        >
          {item}
        </li>
      ))}
    </ul>
  </div>
);
