"use client";

import { X } from "lucide-react";
import { Dialog as SheetPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "~/lib/utils";

export const Sheet = SheetPrimitive.Root;
export const SheetTrigger = SheetPrimitive.Trigger;

/** A right-hand panel over the console; the log stays visible behind a light scrim. */
export function SheetContent({
  title,
  description,
  className,
  children,
  ...props
}: ComponentProps<typeof SheetPrimitive.Content> & { title: ReactNode; description?: ReactNode }) {
  return (
    <SheetPrimitive.Portal>
      <SheetPrimitive.Overlay className="fixed inset-0 z-40 bg-black/30 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <SheetPrimitive.Content
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-[min(460px,94vw)] flex-col border-l border-glass-line bg-panel/95 shadow-[0_8px_30px_rgba(0,0,0,.45)] backdrop-blur-xl outline-none",
          "data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:animate-in data-[state=open]:slide-in-from-right",
          className,
        )}
        {...props}
      >
        <div className="flex items-start gap-3 border-b border-glass-line px-5 py-4">
          <div className="min-w-0 flex-1">
            <SheetPrimitive.Title className="text-[15px] font-[650]">{title}</SheetPrimitive.Title>
            <SheetPrimitive.Description className={cn("mt-0.5 text-xs text-faint", !description && "sr-only")}>
              {description ?? title}
            </SheetPrimitive.Description>
          </div>
          <SheetPrimitive.Close className="grid size-7 cursor-pointer place-items-center rounded-lg text-muted hover:bg-white/5 hover:text-text">
            <X className="size-4" />
            <span className="sr-only">Close</span>
          </SheetPrimitive.Close>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </SheetPrimitive.Content>
    </SheetPrimitive.Portal>
  );
}

export function Section({ title, hint, children }: { title: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-5">
      <h3 className="mb-2 flex items-baseline gap-2 text-xs font-semibold tracking-wide text-muted uppercase">
        {title}
        {hint && <span className="font-normal tracking-normal text-faint normal-case">{hint}</span>}
      </h3>
      {children}
    </section>
  );
}
