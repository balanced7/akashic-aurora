import {
  Github,
  Handshake,
  MessageCircleQuestion,
  ShieldAlert,
} from "lucide-react";

import { withI18n } from "@akashic-labs/i18n/with-i18n";

import { getMetadata } from "~/lib/metadata";
import { ContactForm } from "~/modules/marketing/contact/contact-form";
import { links, routes } from "~/modules/marketing/content/site";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { Container, Section } from "~/modules/marketing/ui/primitives";

export const generateMetadata = getMetadata({
  title: "Contact",
  description:
    "Talk to the people who build Aurora: long-lived design partnerships, private security reports and questions.",
  canonical: routes.contact,
});

const reasons = [
  {
    icon: Handshake,
    title: "Design partners",
    body: "You run a long-lived fleet and want to shape what we build next.",
  },
  {
    icon: ShieldAlert,
    title: "Security reports",
    body: "Found a vulnerability? Tell us here, not in a public issue.",
  },
  {
    icon: MessageCircleQuestion,
    title: "Questions",
    body: "Anything the docs and FAQ did not answer.",
  },
];

const ContactPage = () => (
  <>
    <PageHero
      backdrop="curtains"
      eyebrow="Contact"
      title={
        <>
          Talk to the people
          <span className="text-mk-muted"> who build Aurora</span>
        </>
      }
      description="We read every message. For bugs and feature ideas, GitHub is faster and helps everyone."
    />
    <Section className="pt-0 sm:pt-0 lg:pt-0">
      <Container className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="flex flex-col gap-4">
          {reasons.map((reason) => (
            <div key={reason.title} className="mk-card flex gap-4 p-6">
              <reason.icon
                className="text-hud-cyan mt-0.5 size-5 shrink-0"
                strokeWidth={1.6}
              />
              <div className="flex flex-col gap-1">
                <span className="text-[16px] font-medium text-white">
                  {reason.title}
                </span>
                <span className="text-mk-muted text-[14.5px] leading-relaxed">
                  {reason.body}
                </span>
              </div>
            </div>
          ))}
          <a
            href={links.issues}
            target="_blank"
            rel="noopener noreferrer"
            className="mk-card mk-card-hover flex items-center gap-4 p-6"
          >
            <Github className="size-5 text-white/70" />
            <span className="flex flex-col">
              <span className="text-[16px] font-medium text-white">
                Bugs and ideas
              </span>
              <span className="text-mk-faint text-[13.5px]">
                Open an issue on GitHub
              </span>
            </span>
          </a>
        </div>
        <HudFrame className="[--hud-cut:18px]">
          <div
            data-testid="contact-form"
            className="flex flex-col gap-6 p-7 sm:p-10"
          >
            <HudLabel>Send a message</HudLabel>
            <ContactForm />
          </div>
        </HudFrame>
      </Container>
    </Section>
  </>
);

export default withI18n(ContactPage);
