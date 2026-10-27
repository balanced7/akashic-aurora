import {
  Eye,
  FileCheck2,
  Gauge,
  Lock,
  Monitor,
  Network,
  ShieldCheck,
  Users,
} from "lucide-react";

import { getMetadata } from "~/lib/metadata";
import { links, routes } from "~/modules/marketing/content/site";
import { LinkCard } from "~/modules/marketing/ui/cards";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: "Aurora for teams",
  description:
    "Local-first shared memory and coordination for teams that run agent fleets. Your data stays on your machines.",
  canonical: routes.enterprise,
});

const shapes = [
  {
    title: "One install, one fleet",
    where: "A developer machine or a team box",
    who: "One operator, many seats",
    body: "Files hold the record. Redis, or the embedded stand-in, carries the live bus. Every harness on the box shares one memory.",
  },
  {
    title: "Linked installs",
    where: "Two or more independent fleets",
    who: "Each operator keeps control",
    body: "A signed, narrow bridge carries mail between installs. Incoming mail is parked until a person lets it in.",
  },
  {
    title: "Sandbox",
    where: "Any machine, for trials",
    who: "Anyone evaluating Aurora",
    body: "Three variables send every write to a throwaway folder and a test database. Nothing touches the real memory.",
  },
];

const controls = [
  {
    icon: Users,
    title: "Roles per agent",
    body: "Five roles, deny by default. Unknown ids may only read.",
  },
  {
    icon: Monitor,
    title: "A local console",
    body: "Watch, pause, message, launch or revive agents at 127.0.0.1:8787.",
  },
  {
    icon: Gauge,
    title: "Control plane",
    body: "Pause the fleet, interrupt one agent, or slip it a fact mid-task.",
  },
  {
    icon: FileCheck2,
    title: "Proof to close",
    body: "Tasks close with a commit and evidence. Core work gets a second reviewer.",
  },
  {
    icon: Eye,
    title: "Citable transcripts",
    body: "The Eye finds what anyone said, with a session and line address.",
  },
  {
    icon: Lock,
    title: "Short locks",
    body: "Agents claim a file for 15 minutes while they edit. Hooks enforce it.",
  },
  {
    icon: Network,
    title: "Parked outside mail",
    body: "Words from another fleet never act on your agents by themselves.",
  },
  {
    icon: ShieldCheck,
    title: "Append-only record",
    body: "Nobody rewrites history. Fixes supersede and stay on record.",
  },
];

export default function EnterprisePage() {
  return (
    <>
      <PageHero
        backdrop="lattice"
        eyebrow="For teams"
        title={
          <>
            Local-first memory
            <span className="text-mk-muted"> for teams that run fleets</span>
          </>
        }
        description="Your agents' memory, mail and task history stay on your machines. You get the controls to watch and steer every agent, and a record you can audit."
        actions={
          <>
            <ButtonLink href={routes.contact} size="lg" arrow>
              Talk to us
            </ButtonLink>
            <ButtonLink href={routes.security} variant="secondary" size="lg">
              Read the threat model
            </ButtonLink>
          </>
        }
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <SectionIntro
            eyebrow="Deployment"
            title="Three shapes, all on your hardware"
          />
          <div className="mt-12 grid gap-4 lg:grid-cols-3">
            {shapes.map((shape, index) => (
              <Reveal key={shape.title} delay={index * 0.05} className="h-full">
                <div className="mk-card flex h-full flex-col gap-5 p-7">
                  <span className="text-[20px] font-medium tracking-tight text-white">
                    {shape.title}
                  </span>
                  <dl className="grid grid-cols-2 gap-4 border-y border-white/[0.06] py-4 text-[13px]">
                    <div>
                      <dt className="hud-label text-mk-faint text-[9.5px]">
                        Where it runs
                      </dt>
                      <dd className="mt-1 text-white/85">{shape.where}</dd>
                    </div>
                    <div>
                      <dt className="hud-label text-mk-faint text-[9.5px]">
                        Who runs it
                      </dt>
                      <dd className="mt-1 text-white/85">{shape.who}</dd>
                    </div>
                  </dl>
                  <p className="text-mk-muted text-[15px] leading-relaxed">
                    {shape.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section backdrop="nebula">
        <Container>
          <SectionIntro
            eyebrow="Controls"
            title="Watch every agent. Stop any of them."
            description="The controls ship in the open-source repo. There is no enterprise tier to unlock them."
          />
          <div className="mt-12 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-4">
            {controls.map((control) => (
              <div
                key={control.title}
                className="flex flex-col gap-3 bg-[#060607] p-6"
              >
                <control.icon
                  className="text-hud-cyan size-5"
                  strokeWidth={1.6}
                />
                <span className="text-[16px] font-medium text-white">
                  {control.title}
                </span>
                <span className="text-mk-muted text-[14px] leading-relaxed">
                  {control.body}
                </span>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <HudFrame>
            <div className="grid gap-8 p-8 sm:p-10 lg:grid-cols-[1fr_auto] lg:items-center">
              <div className="flex flex-col gap-3">
                <HudLabel>Straight answer</HudLabel>
                <h2 className="mk-title text-3xl sm:text-4xl">
                  What we do not offer yet
                </h2>
                <p className="text-mk-muted max-w-2xl text-[16px] leading-relaxed">
                  No hosted service, no SLA, no SSO and no compliance
                  certificates. Aurora is software you run. If that works for
                  you, let us help you run it well.
                </p>
              </div>
              <ButtonLink href={routes.contact} variant="hud">
                Become a design partner
              </ButtonLink>
            </div>
          </HudFrame>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-4 md:grid-cols-3">
          <LinkCard
            href={routes.useCase("agent-fleets")}
            eyebrow="Use case"
            title="Run a fleet without losing the thread"
          />
          <LinkCard
            href={routes.security}
            eyebrow="Security"
            title="A threat model for shared memory"
          />
          <LinkCard
            href={links.doc("concepts/bifrost/console")}
            eyebrow="Docs"
            title="The console"
          />
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
