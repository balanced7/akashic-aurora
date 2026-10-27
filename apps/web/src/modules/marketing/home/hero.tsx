import { ArrowRight, Github } from "lucide-react";
import Link from "next/link";

import { positioning } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { FleetConsole } from "~/modules/marketing/home/fleet-console";
import { HeroSetup } from "~/modules/marketing/home/hero-setup";
import { AuroraBackdrop } from "~/modules/marketing/ui/aurora-backdrop";
import { ButtonLink, Container } from "~/modules/marketing/ui/primitives";
import { ShaderBackground } from "~/modules/marketing/ui/shader-background";

import type { CSSProperties, ReactNode } from "react";

/** One orchestrated page load: each piece rises in sequence. Pure CSS, so it runs before hydration. */
const Rise = ({
  delay,
  children,
  className,
  solid,
}: {
  delay: number;
  children: ReactNode;
  className?: string;
  solid?: boolean;
}) => (
  <div
    className={`${solid ? "mk-rise-solid" : "mk-rise"} ${className ?? ""}`}
    style={{ "--rise-delay": `${delay}ms` } as CSSProperties}
  >
    {children}
  </div>
);

/** Masked word rise for the headline: each word slides up from behind its own clip. */
const Words = ({
  text,
  start,
  step = 70,
  className,
}: {
  text: string;
  start: number;
  step?: number;
  className?: string;
}) => (
  <>
    {text.split(" ").map((word, index) => (
      <span key={`${word}-${index}`} className="mk-word-mask">
        <span
          className={`mk-word-rise ${className ?? ""}`}
          style={
            { "--rise-delay": `${start + index * step}ms` } as CSSProperties
          }
        >
          {word}&nbsp;
        </span>
      </span>
    ))}
  </>
);

const stats = [
  { term: "License", value: "Apache-2.0" },
  { term: "Runs on", value: "Your machine" },
  { term: "Residents", value: "6 · as of 2026-10-20" },
];

export const Hero = () => (
  <section
    data-testid="hero"
    className="relative isolate overflow-hidden pt-32 pb-20 sm:pt-40 lg:pb-28"
  >
    <AuroraBackdrop intensity={0.45} className="-z-10" />
    <ShaderBackground
      preset="aurora"
      intensity={0.9}
      fade="bottom"
      className="h-[90%] opacity-50 mix-blend-screen md:opacity-90"
    />
    <Container className="relative">
      <Rise delay={0}>
        <Link
          href={routes.pillar("knowledge")}
          className="group mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-black/30 py-1 pr-3 pl-1 text-[13px] text-white/75 backdrop-blur-md transition-colors hover:border-white/15 hover:text-white"
        >
          <span className="hud-label bg-hud-gold/15 text-hud-gold rounded-full px-2 py-0.5 text-[10px]">
            Core
          </span>
          The memory loop, running today
          <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </Rise>

      <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <h1
            className="mk-display text-[2.7rem] sm:text-7xl lg:text-[5.2rem]"
            data-testid="hero-title"
          >
            <Words text="A home for" start={60} step={45} />
            <br />
            <span className="mk-word-mask">
              <span
                className="mk-word-rise mk-gradient-text"
                style={{ "--rise-delay": "200ms" } as CSSProperties}
              >
                your agents.
              </span>
            </span>
            <br />
            <Words
              text="One that remembers."
              start={280}
              step={45}
              className="text-mk-muted"
            />
          </h1>
          <Rise delay={420} solid>
            <p className="text-mk-muted mt-7 max-w-2xl text-lg leading-relaxed text-pretty sm:text-xl">
              {positioning.subheadline}
            </p>
          </Rise>
          <Rise delay={500} className="mt-9 flex flex-wrap items-center gap-3">
            <ButtonLink href={links.doc("quickstart")} size="lg" arrow>
              Get started in two minutes
            </ButtonLink>
            <a
              href={links.repo}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.06] px-5 text-[15px] font-medium text-white backdrop-blur-md transition-colors hover:bg-white/[0.12]"
            >
              <Github className="size-4" />
              Star on GitHub
            </a>
          </Rise>
          <Rise delay={560} className="mt-5">
            <HeroSetup />
          </Rise>
        </div>

        <dl className="hidden flex-col gap-3 text-right text-[13px] lg:flex">
          {stats.map((stat, index) => (
            <Rise key={stat.term} delay={540 + index * 60}>
              <dt className="text-mk-faint">{stat.term}</dt>
              <dd className="font-medium text-white">{stat.value}</dd>
            </Rise>
          ))}
        </dl>
      </div>

      <Rise delay={600} className="mt-16 sm:mt-20">
        <FleetConsole />
      </Rise>
    </Container>
  </section>
);
