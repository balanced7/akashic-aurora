import { HardDrive, ShieldAlert, TriangleAlert } from "lucide-react";

import { getMetadata } from "~/lib/metadata";
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
  title: "Security: a threat model for shared agent memory",
  description:
    "Shared memory gives agents a new attack surface. Here is how Aurora handles bad lessons, injected text, outside mail and unknown agents, and where its limits are.",
  canonical: routes.security,
});

/** Each control maps to a documented mechanism. Caveats are quoted or condensed from the docs. */
const threats = [
  {
    threat: "A bad lesson spreads",
    risk: "One agent writes wrong advice. Every agent after it reads it.",
    controls: [
      "Every packed line keeps a pointer to its source, so you can trace it.",
      "A rule-based critic drops lines that have no source.",
      "Lessons that never help lose rank and get benched.",
      "Fixes supersede. The bad version stays on record for review.",
    ],
    caveat:
      "Credit measures outcomes, not truth. A person still reviews what matters.",
    doc: "concepts/memory/ranker-and-distiller",
  },
  {
    threat: "Injected text from the web",
    risk: "A fetched page carries instructions aimed at your agents.",
    controls: [
      "The web door issues a receipt for every fetch.",
      "Fetched text is marked untrusted before an agent reads it.",
    ],
    caveat: "Marking is a signal to the agent, not a sandbox.",
    doc: "concepts/tools/web-door",
  },
  {
    threat: "Mail from another fleet",
    risk: "Words from outside try to act on your agents.",
    controls: [
      "The bridge is a signed, narrow, outbound-only link.",
      "Incoming mail is parked, not delivered.",
      "A person decides when it comes in.",
    ],
    caveat: "The bridge's sealed envelope is built, not wired.",
    doc: "concepts/bifrost/bridge",
  },
  {
    threat: "An agent you don't know",
    risk: "A new or spoofed id starts writing to shared memory.",
    controls: [
      "Five roles, deny by default.",
      "An id Aurora does not know may only read.",
    ],
    caveat:
      "Trust is not a security wall. Only runner tools check capabilities.",
    doc: "concepts/coordination/trust",
  },
  {
    threat: "Two agents, one file",
    risk: "Parallel edits clobber each other.",
    controls: [
      "Advisory 15-minute locks while an agent edits.",
      "The edit and commit hooks refuse a file a peer holds.",
    ],
    caveat: "Fencing tokens are minted but not yet checked.",
    doc: "concepts/coordination/locks",
  },
  {
    threat: "Silent failure",
    risk: "A helper breaks and the agent acts on half the picture.",
    controls: [
      "Fail soft: the main work carries on with less and says what it lost.",
      "Partial query answers carry a degraded flag. Failures print UNAVAILABLE.",
    ],
    caveat: "A degraded answer is still partial. Treat it that way.",
    doc: "concepts/foundations/fail-soft",
  },
];

const faq = [
  {
    question: "Where does Aurora keep its data?",
    answer:
      "In local files on your machine, and in your Redis when it is up. Every write goes to a file first. There is no hosted Aurora service.",
  },
  {
    question: "Does anything leave my machine?",
    answer:
      "Only when you use a verb that reaches out. ask sends a question to a helper model you configure. web fetch and web search reach the web, and search can use a Brave API key. The memory itself stays local.",
  },
  {
    question: "Is Aurora SOC 2 certified?",
    answer:
      "No. Aurora is open-source software you run yourself, not a hosted service. Your own controls cover where it runs.",
  },
  {
    question: "Can I keep experiments away from the real memory?",
    answer:
      "Yes. Set REDIS_DB, AI_SETUP and AKASHIC_RECALL_STATE_DIR, and every write goes to a throwaway folder and a test database.",
  },
  {
    question: "Is the record tamper-proof?",
    answer:
      "It is append-only by design: nobody rewrites an event, and fixes supersede. We do not claim cryptographic tamper-proofing for local files.",
  },
  {
    question: "How do I report a vulnerability?",
    answer:
      "Please do not open a public issue. Contact the maintainers privately through the contact page, and we will reply there.",
  },
];

export default function SecurityPage() {
  return (
    <>
      <PageHero
        eyebrow="Security"
        title={
          <>
            Shared memory is a new attack surface.
            <span className="text-mk-muted"> Here is our threat model.</span>
          </>
        }
        description="When agents share what they learn, a bad lesson can spread and outside text can try to steer them. These are the controls Aurora ships, and the limits the docs admit."
        aside={
          <HudFrame tone="cyan" className="lg:w-[320px]">
            <div className="flex flex-col gap-4 p-6">
              <HardDrive className="text-hud-cyan size-6" strokeWidth={1.5} />
              <span className="text-[18px] font-medium text-white">
                Your disk, your Redis
              </span>
              <span className="text-mk-muted text-[14px] leading-relaxed">
                No hosted service. Every write lands in a local file first.
              </span>
            </div>
          </HudFrame>
        }
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="grid gap-4 md:grid-cols-2">
          {threats.map((item, index) => (
            <Reveal key={item.threat} delay={index * 0.04} className="h-full">
              <article className="mk-card flex h-full flex-col gap-5 p-7">
                <header className="flex items-start gap-3">
                  <ShieldAlert
                    className="text-hud-gold mt-1 size-5 shrink-0"
                    strokeWidth={1.6}
                  />
                  <div className="flex flex-col gap-1">
                    <h2 className="text-[20px] font-medium tracking-tight text-white">
                      {item.threat}
                    </h2>
                    <p className="text-mk-faint text-[14px]">{item.risk}</p>
                  </div>
                </header>
                <ul className="flex flex-col gap-2.5">
                  {item.controls.map((control) => (
                    <li
                      key={control}
                      className="flex gap-3 text-[14.5px] leading-relaxed text-white/85"
                    >
                      <span className="hud-gem mt-2 shrink-0 scale-75" />
                      {control}
                    </li>
                  ))}
                </ul>
                <div className="mt-auto flex items-start gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
                  <TriangleAlert className="text-hud-gold mt-0.5 size-4 shrink-0" />
                  <span className="text-mk-muted text-[13.5px] leading-relaxed">
                    {item.caveat}
                  </span>
                </div>
                <a
                  href={links.doc(item.doc)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-mk-faint font-mono text-[10.5px] hover:text-white"
                >
                  docs/{item.doc}
                </a>
              </article>
            </Reveal>
          ))}
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
          <div className="flex flex-col gap-6">
            <SectionIntro
              eyebrow="For your security team"
              title="Questions they will ask"
            />
            <HudLabel tone="muted">Answers from the docs and README</HudLabel>
            <ButtonLink href={routes.contact} variant="secondary" arrow>
              Contact the maintainers
            </ButtonLink>
          </div>
          <FaqList items={faq} />
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
