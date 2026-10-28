import { AuroraBackdrop } from "~/modules/marketing/ui/aurora-backdrop";
import { HudBadge, HudFrame } from "~/modules/marketing/ui/hud";
import { ButtonLink } from "~/modules/marketing/ui/primitives";

import type { ReactNode } from "react";

interface SignalLostProps {
  readonly code: string;
  readonly title: ReactNode;
  readonly description: string;
  readonly command: string;
  readonly output: string;
  readonly action?: ReactNode;
}

/** Shared empty state for 404 and errors, in Aurora's own voice. */
export const SignalLost = ({
  code,
  title,
  description,
  command,
  output,
  action,
}: SignalLostProps) => (
  <section
    data-testid="signal-lost"
    className="relative flex min-h-[86vh] items-center overflow-hidden pt-32 pb-20"
  >
    <AuroraBackdrop intensity={0.4} />
    <div className="mk-container relative grid items-center gap-12 lg:grid-cols-[1.1fr_1fr]">
      <div className="flex flex-col items-start gap-6">
        <HudBadge>{code}</HudBadge>
        <h1 className="mk-display text-5xl sm:text-7xl">{title}</h1>
        <p className="text-mk-muted max-w-lg text-lg leading-relaxed">
          {description}
        </p>
        <div className="flex flex-wrap gap-3">
          {action}
          <ButtonLink href="/" size="lg" arrow>
            Back to the start
          </ButtonLink>
          <ButtonLink href="/docs" variant="secondary" size="lg">
            Browse the docs
          </ButtonLink>
        </div>
        <p className="text-mk-faint text-[13px]">
          Or press{" "}
          <kbd className="rounded border border-white/10 px-1 font-mono text-[11px]">
            ⌘K
          </kbd>{" "}
          to search.
        </p>
      </div>
      <HudFrame scan className="[--hud-cut:16px]">
        <div className="hud-scanlines flex flex-col gap-2 p-6 font-mono text-[13px] leading-relaxed sm:p-8">
          <div className="text-white">
            <span className="text-hud-cyan">$ </span>
            {command}
          </div>
          <div className="text-white/70">{output}</div>
          <div className="mt-2">
            <span className="text-hud-cyan">$ </span>
            <span className="animate-mk-blink inline-block h-4 w-2 translate-y-0.5 bg-white/80" />
          </div>
        </div>
      </HudFrame>
    </div>
  </section>
);
