import { withI18n } from "@akashic-labs/i18n/with-i18n";

import { getMetadata } from "~/lib/metadata";
import { positioning } from "~/modules/marketing/content/aurora";
import { homeFaq } from "~/modules/marketing/content/faq";
import { links, routes } from "~/modules/marketing/content/site";
import { Constellation } from "~/modules/marketing/home/constellation";
import { FleetSection } from "~/modules/marketing/home/fleet-section";
import { GetStarted } from "~/modules/marketing/home/get-started";
import { HarnessStrip } from "~/modules/marketing/home/harness-strip";
import { Hero } from "~/modules/marketing/home/hero";
import { HonestStatus } from "~/modules/marketing/home/honest-status";
import { LoopReplay } from "~/modules/marketing/home/loop-replay";
import { MemoryTeamWorld } from "~/modules/marketing/home/memory-team-world";
import { PillarBento } from "~/modules/marketing/home/pillar-bento";
import { PrinciplesMarquee } from "~/modules/marketing/home/principles-marquee";
import { RecallScoreboard } from "~/modules/marketing/home/recall-scoreboard";
import { TrustLadder } from "~/modules/marketing/home/trust-ladder";
import { Playground } from "~/modules/marketing/playground/playground";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { FaqList } from "~/modules/marketing/ui/faq-list";
import {
  Container,
  Eyebrow,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const generateMetadata = getMetadata({
  title: positioning.tagline,
  description: positioning.subheadline,
  canonical: routes.home,
});

const HomePage = () => {
  return (
    <>
      <Hero />
      <HarnessStrip />
      <MemoryTeamWorld />
      <Constellation />

      <Section>
        <Container>
          <SectionIntro
            eyebrow="Watch the loop close"
            title="One agent learns. Another agent benefits."
            description="The memory loop is still the core. Claude Code hits a snag on Monday and writes it down. On Wednesday, Codex is about to make the same mistake. Aurora steps in first."
          />
          <Reveal className="mt-14">
            <LoopReplay />
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-center lg:gap-14">
          <div className="flex flex-col gap-6">
            <SectionIntro
              eyebrow="Try it here"
              title={
                <>
                  Teach it a lesson.
                  <br />
                  <span className="text-mk-muted">Watch it come back.</span>
                </>
              }
              description="Type real Aurora commands. Record a lesson, then touch a file it fits. Touch one it does not fit, and Aurora stays quiet."
            />
            <ol className="text-mk-muted flex flex-col gap-2 text-[14.5px]">
              <li>
                <span className="font-hud text-hud-gold mr-2 text-[12px]">
                  01
                </span>
                learn a lesson
              </li>
              <li>
                <span className="font-hud text-hud-gold mr-2 text-[12px]">
                  02
                </span>
                recall-at a file it fits
              </li>
              <li>
                <span className="font-hud text-hud-gold mr-2 text-[12px]">
                  03
                </span>
                recall-at a file it does not
              </li>
            </ol>
          </div>
          <Reveal>
            <Playground />
          </Reveal>
        </Container>
      </Section>

      <RecallScoreboard />
      <PillarBento />
      <FleetSection />
      <TrustLadder />
      <HonestStatus />
      <GetStarted />
      <PrinciplesMarquee />

      <Section>
        <Container className="grid gap-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
          <div className="flex flex-col gap-5">
            <Eyebrow>FAQ</Eyebrow>
            <h2 className="mk-title text-4xl sm:text-[2.6rem]">
              Questions,
              <br />
              <span className="text-mk-muted">answered plainly.</span>
            </h2>
            <p className="text-mk-muted text-[15px]">
              Something missing?{" "}
              <a
                href={links.discussions}
                className="text-white underline decoration-white/40 underline-offset-4 hover:decoration-white"
              >
                Ask on GitHub
              </a>
              .
            </p>
          </div>
          <FaqList items={homeFaq} />
        </Container>
      </Section>

      <CtaBand />
    </>
  );
};

export default withI18n(HomePage);
