import { Github } from "lucide-react";

import { links } from "~/modules/marketing/content/site";
import { AuroraBackdrop } from "~/modules/marketing/ui/aurora-backdrop";
import { AuroraMark } from "~/modules/marketing/ui/brand";
import { HudDivider } from "~/modules/marketing/ui/hud";
import { ButtonLink, Container } from "~/modules/marketing/ui/primitives";

interface CtaBandProps {
  readonly title?: string;
  readonly description?: string;
}

export const CtaBand = ({
  title = "Give your agents a home",
  description = "Shared memory, a message bus and a trust layer, on your machine. Two minutes to a first session.",
}: CtaBandProps) => (
  <section
    data-testid="cta-band"
    className="relative overflow-hidden py-28 sm:py-36"
  >
    <AuroraBackdrop intensity={0.8} />
    <Container className="relative flex flex-col items-center text-center">
      <AuroraMark className="size-14" />
      <h2 className="mk-display mt-8 max-w-3xl text-4xl sm:text-6xl">
        {title}
      </h2>
      <p className="text-mk-muted mt-5 max-w-xl text-lg">{description}</p>
      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <ButtonLink href={links.doc("quickstart")} variant="hud">
          Start the quickstart
        </ButtonLink>
        <a
          href={links.repo}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.06] px-4 text-[14px] font-medium text-white transition-colors hover:bg-white/[0.12]"
        >
          <Github className="size-4" />
          View the source
        </a>
      </div>
      <HudDivider className="mt-16 w-full max-w-md" />
    </Container>
  </section>
);
