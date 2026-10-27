import {
  Crosshair,
  Eye,
  FileStack,
  Fingerprint,
  HardDrive,
  Network,
  Sigma,
  TrendingUp,
} from "lucide-react";

import { differentiators } from "~/modules/marketing/content/aurora";
import { links } from "~/modules/marketing/content/site";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

const icons = [
  Crosshair,
  TrendingUp,
  Sigma,
  HardDrive,
  Network,
  FileStack,
  Fingerprint,
  Eye,
];

export const Differentiators = () => (
  <Section>
    <Container>
      <SectionIntro
        eyebrow="What makes it different"
        title={
          <>
            Not another memory API.
            <br />
            <span className="text-mk-muted">
              It acts before your agent does.
            </span>
          </>
        }
        description="Most memory layers store facts and wait to be asked. Aurora pushes the right lesson at the right moment, then checks whether it helped."
      />
      <div className="mt-14 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-4">
        {differentiators.map((item, index) => {
          const Icon = icons[index] ?? Crosshair;
          return (
            <Reveal key={item.title} delay={index * 0.04} className="h-full">
              <a
                href={links.doc(item.doc)}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex h-full flex-col gap-4 bg-[#060607] p-6 transition-colors hover:bg-[#0b0b0d]"
              >
                <Icon
                  className="group-hover:text-hud-cyan size-5 text-white/70 transition-colors"
                  strokeWidth={1.6}
                />
                <span className="text-[17px] font-medium tracking-tight text-white">
                  {item.title}
                </span>
                <span className="text-mk-muted text-[14.5px] leading-relaxed">
                  {item.body}
                </span>
                <span className="text-mk-faint mt-auto font-mono text-[10.5px] group-hover:text-white/60">
                  docs/{item.doc}
                </span>
              </a>
            </Reveal>
          );
        })}
      </div>
    </Container>
  </Section>
);
