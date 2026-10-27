import { cn } from "@akashic-labs/ui";

import type { TerminalLine } from "~/modules/marketing/content/aurora";

const lineStyles: Record<TerminalLine["kind"], string> = {
  cmd: "text-white",
  out: "text-white/75",
  dim: "text-white/55",
  ok: "text-hud-cyan",
  gold: "text-hud-gold",
  blank: "",
};

interface TerminalProps {
  readonly lines: readonly TerminalLine[];
  readonly title?: string;
  readonly className?: string;
  readonly caret?: boolean;
}

export const Terminal = ({
  lines,
  title = "zsh",
  className,
  caret,
}: TerminalProps) => (
  <div
    className={cn(
      "overflow-hidden rounded-2xl border border-white/[0.08] bg-[#07080a] shadow-[0_30px_80px_-30px_rgb(0_0_0/0.8)]",
      className,
    )}
  >
    <div className="flex items-center gap-2 border-b border-white/[0.06] px-4 py-3">
      <span className="size-2.5 rounded-full bg-white/15" />
      <span className="size-2.5 rounded-full bg-white/15" />
      <span className="size-2.5 rounded-full bg-white/15" />
      <span className="text-mk-faint ml-2 font-mono text-[11px]">{title}</span>
    </div>
    <pre
      tabIndex={0}
      className="overflow-x-auto p-4 font-mono text-[12.5px] leading-6 sm:p-5"
    >
      <code>
        {lines.map((line, index) => (
          <div
            key={`${line.kind}-${index}`}
            className={cn("whitespace-pre-wrap", lineStyles[line.kind])}
          >
            {line.kind === "cmd" && (
              <span className="text-hud-cyan select-none">$ </span>
            )}
            {line.kind === "blank" ? " " : line.text}
          </div>
        ))}
        {caret && (
          <div>
            <span className="text-hud-cyan select-none">$ </span>
            <span className="animate-mk-blink inline-block h-4 w-2 translate-y-0.5 bg-white/80" />
          </div>
        )}
      </code>
    </pre>
  </div>
);
