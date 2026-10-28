"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { cn } from "@akashic-labs/ui";

import { install } from "~/modules/marketing/content/aurora";

const prompt = install.agentPrompt.join("\n");

/** One click copies the quickstart's agent prompt, so the visitor's own agent installs Aurora. */
export const HeroSetup = () => {
  const [isCopied, setIsCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      setIsCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      data-testid="hero-setup"
      aria-label={isCopied ? "Setup prompt copied" : "Copy the setup prompt"}
      className="group hud-frame flex w-full max-w-xl flex-col items-start gap-3 px-4 py-3 text-left [--hud-cut:10px] sm:flex-row sm:items-center"
    >
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-hud text-hud-gold text-[10.5px] font-semibold tracking-[0.16em] uppercase">
          Agent setup
        </span>
        <span className="text-mk-muted text-[13.5px] leading-snug">
          Paste one prompt into Claude Code, Codex or Cursor. It installs Aurora
          and records a first lesson.
        </span>
      </span>
      <span
        className={cn(
          "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2.5 text-[12px] font-medium transition-colors sm:ml-auto",
          isCopied
            ? "bg-hud-cyan/15 text-hud-cyan"
            : "bg-white/[0.08] text-white group-hover:bg-white/[0.14]",
        )}
      >
        {isCopied ? (
          <Check className="size-3.5" />
        ) : (
          <Copy className="size-3.5" />
        )}
        {isCopied ? "Copied" : "Copy prompt"}
      </span>
    </button>
  );
};
