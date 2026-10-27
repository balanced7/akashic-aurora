import { install } from "~/modules/marketing/content/aurora";
import { links } from "~/modules/marketing/content/site";
import { Quickstart } from "~/modules/marketing/home/quickstart";
import { HudLabel } from "~/modules/marketing/ui/hud";
import {
  ButtonLink,
  Container,
  InlineCode,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

const steps = [
  {
    title: "Install uv",
    body: "It handles the Python environment. Nothing else to set up.",
  },
  {
    title: "Run a first session",
    body: "Boot, learn one lesson, recall it. About two minutes.",
  },
  {
    title: "Turn on the push",
    body: (
      <>
        Run <InlineCode>{install.hooks}</InlineCode> so lessons arrive before
        edits.
      </>
    ),
  },
];

export const GetStarted = () => (
  <Section id="get-started">
    <Container>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div className="flex min-w-0 flex-col gap-8">
          <SectionIntro
            eyebrow="Quickstart"
            title={
              <>
                Running in two minutes.
                <br />
                <span className="text-mk-muted">Or let your agent do it.</span>
              </>
            }
            description="Clone it, alias it, run three commands. Or paste one prompt into the agent you already use and let it do the setup."
          />
          <ol className="flex flex-col gap-5">
            {steps.map((step, index) => (
              <li key={step.title} className="flex gap-4">
                <span className="hud-frame flex size-8 shrink-0 items-center justify-center [--hud-cut:7px]">
                  <span className="font-hud text-hud-gold text-[12px] font-semibold">
                    {index + 1}
                  </span>
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[16px] font-medium text-white">
                    {step.title}
                  </span>
                  <span className="text-mk-muted text-[14.5px] leading-relaxed">
                    {step.body}
                  </span>
                </div>
              </li>
            ))}
          </ol>
          <div className="flex flex-wrap items-center gap-3">
            <ButtonLink href={links.doc("quickstart")} arrow>
              Read the quickstart
            </ButtonLink>
            <ButtonLink href={links.doc("tutorial")} variant="secondary">
              Ten-minute tutorial
            </ButtonLink>
          </div>
          <HudLabel tone="muted" className="text-[10px]">
            Windows, macOS and Linux · Python 3.12 via uv
          </HudLabel>
        </div>
        <Reveal className="min-w-0">
          <Quickstart />
        </Reveal>
      </div>
    </Container>
  </Section>
);
