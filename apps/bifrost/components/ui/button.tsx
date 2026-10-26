import { type VariantProps, cva } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "~/lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-lg border font-semibold whitespace-nowrap transition outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "border-border bg-panel2/80 text-text hover:border-[#39405a] hover:bg-panel2",
        ghost: "border-transparent bg-transparent text-muted hover:bg-white/5 hover:text-text",
        warn: "border-amber/45 bg-amber/10 text-amber hover:bg-amber/15",
        primary: "border-accent/40 bg-accent/15 text-accent hover:bg-accent/25",
      },
      size: {
        sm: "h-7 px-2.5 text-xs",
        md: "h-8 px-3 text-[13px]",
        icon: "size-8 text-[13px]",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export function Button({
  className,
  variant,
  size,
  ...props
}: ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return <button type="button" className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
