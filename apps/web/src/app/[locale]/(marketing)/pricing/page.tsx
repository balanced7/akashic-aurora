import { Check, Minus } from "lucide-react";

import { cn } from "@akashic-labs/ui";

import { getMetadata } from "~/lib/metadata";
import { liveNumbers } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { FaqList } from "~/modules/marketing/ui/faq-list";
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
  title: "Pricing",
  description:
    "Aurora is free and open source under Apache-2.0. Every feature is in the repo. No hosted tier holds anything back.",
  canonical: routes.pricing,
});

const included = [
  "Memory, recall and recall at action",
  "Flip credit, the recall loop and curation",
  "Bifrost: bus, seats, handoffs, runners, console",
  "Coordination: task ledger, locks, trust",
  "Story: narrative spine, episodes, the Eye",
  "House tools: web door, manuals shelf, discover",
  `${liveNumbers.cliVerbs} CLI verbs and ${liveNumbers.mcpTools} MCP tools`,
  "Sandbox mode and the full test suite",
];

const faq = [
  {
    question: "Is Aurora really free?",
    answer:
      "Yes. It is open source under Apache-2.0. Clone it, run it, fork it and ship it.",
  },
  {
    question: "What does the open-source version leave out?",
    answer:
      "Nothing that exists today. Every feature on this site is in the public repo.",
  },
  {
    question: "Is there a hosted version?",
    answer:
      "No. Aurora runs on your machine. If you need a managed cloud with an SLA today, a hosted memory API will fit you better.",
  },
  {
    question: "What does it cost to run?",
    answer:
      "Your own compute. The core needs uv and Python. Redis is optional. Verbs that call a helper model, like ask, use the model and keys you configure.",
  },
  {
    question: "What is a design partner?",
    answer:
      "A team running a real agent fleet that works with the maintainers directly. You get a direct line, and we learn what to build next. Talk to us to see if it fits.",
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        eyebrow="Pricing"
        title={
          <>
            Free and open source.
            <span className="text-mk-muted"> Every feature, no gates.</span>
          </>
        }
        description="No seat fees, no usage meters, no hosted tier that holds features back. What is in the repo is the product."
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="grid gap-4 lg:grid-cols-3">
          <Reveal className="h-full">
            <HudFrame
              data-testid="plan-open-source"
              className="h-full [--hud-cut:18px]"
            >
              <div className="flex h-full flex-col gap-6 p-8">
                <div className="flex items-center justify-between">
                  <span className="text-[18px] font-medium text-white">
                    Open source
                  </span>
                  <HudLabel>Most teams</HudLabel>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-hud text-hud-gold-bright hud-glow-gold text-6xl font-semibold">
                    $0
                  </span>
                  <span className="text-mk-faint text-[14px]">forever</span>
                </div>
                <p className="text-mk-muted text-[15px]">
                  The whole system, on your machine, under Apache-2.0.
                </p>
                <ul className="flex flex-col gap-2.5">
                  {included.map((item) => (
                    <li
                      key={item}
                      className="flex gap-2.5 text-[14px] text-white/85"
                    >
                      <Check className="text-hud-cyan mt-0.5 size-4 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <ButtonLink
                  href={links.doc("quickstart")}
                  className="mt-auto w-full"
                  size="lg"
                  arrow
                >
                  Get started
                </ButtonLink>
              </div>
            </HudFrame>
          </Reveal>

          <Reveal delay={0.06} className="h-full">
            <div
              data-testid="plan-design-partner"
              className="mk-card flex h-full flex-col gap-6 p-8"
            >
              <span className="text-[18px] font-medium text-white">
                Design partner
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-semibold tracking-tight text-white">
                  Let&apos;s talk
                </span>
              </div>
              <p className="text-mk-muted text-[15px]">
                For teams running a real agent fleet who want to shape what
                comes next.
              </p>
              <ul className="flex flex-col gap-2.5">
                {[
                  "Everything in open source",
                  "A direct line to the maintainers",
                  "Help wiring Aurora into your repo",
                  "A voice in the fleet benchmark",
                ].map((item) => (
                  <li
                    key={item}
                    className="flex gap-2.5 text-[14px] text-white/85"
                  >
                    <Check className="text-hud-cyan mt-0.5 size-4 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <ButtonLink
                href={routes.contact}
                variant="secondary"
                className="mt-auto w-full"
                size="lg"
                arrow
              >
                Contact us
              </ButtonLink>
            </div>
          </Reveal>

          <Reveal delay={0.12} className="h-full">
            <div
              data-testid="plan-hosted"
              className="mk-card flex h-full flex-col gap-6 border-dashed p-8"
            >
              <span className="text-[18px] font-medium text-white/70">
                Hosted Aurora
              </span>
              <span className="text-5xl font-semibold tracking-tight text-white/55">
                Not offered
              </span>
              <p className="text-mk-muted text-[15px]">
                We do not run Aurora for you today. Your memory stays on your
                disk. If you need a managed service with an SLA right now, a
                hosted memory API is the better pick.
              </p>
              <ul className="flex flex-col gap-2.5">
                {[
                  "No managed cloud",
                  "No SLA",
                  "No data leaves your machine through us",
                ].map((item) => (
                  <li
                    key={item}
                    className={cn("text-mk-faint flex gap-2.5 text-[14px]")}
                  >
                    <Minus className="mt-0.5 size-4 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <ButtonLink
                href={routes.compare}
                variant="ghost"
                className="mt-auto"
                arrow
              >
                Compare approaches
              </ButtonLink>
            </div>
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
          <SectionIntro eyebrow="FAQ" title="Money questions" />
          <FaqList items={faq} />
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
