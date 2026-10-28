"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { cn } from "@akashic-labs/ui";

export const CopyButton = ({
  text,
  className,
  label = "Copy",
}: {
  text: string;
  className?: string;
  label?: string;
}) => {
  const [isCopied, setIsCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 1600);
    } catch {
      setIsCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={isCopied ? "Copied" : label}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 text-[12px] font-medium text-white/80 transition-colors hover:bg-white/[0.1] hover:text-white",
        className,
      )}
    >
      {isCopied ? (
        <Check className="text-hud-cyan size-3.5" />
      ) : (
        <Copy className="size-3.5" />
      )}
      {isCopied ? "Copied" : label}
    </button>
  );
};
