import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

export const tradeOffs = [
  {
    versus: "Build it yourself",
    body: "Home-grown memory starts as a JSON file and a grep. Then you need ranking, a floor, dedupe, credit, locks and handoffs. Aurora has all of that, in the open.",
    trade: "Adopt a young open-source project, or own the plumbing for good.",
  },
  {
    versus: "A hosted memory API",
    body: "Hosted APIs store facts and answer queries. Aurora runs on your disk, pushes lessons at the moment of action and coordinates agents.",
    trade: "No managed cloud and no SLA. You run it, and your data stays put.",
  },
  {
    versus: "Do nothing",
    body: "Rules files and long chats work for one agent. Once two agents share a repo, the fix one finds never reaches the other.",
    trade: "Keep paying for the same mistake, or add three commands.",
  },
] as const;

export const TradeOffs = () => (
  <Section>
    <Container>
      <SectionIntro
        eyebrow="Honest options"
        title={
          <>
            Three ways to handle agent memory.
            <br />
            <span className="text-mk-muted">Each one costs something.</span>
          </>
        }
        description="Here is what each choice costs, so you can pick with open eyes."
      />
      <div className="mt-14 grid gap-4 lg:grid-cols-3">
        {tradeOffs.map((item, index) => (
          <Reveal key={item.versus} delay={index * 0.06} className="h-full">
            <div className="mk-card flex h-full flex-col gap-5 p-7">
              <span className="text-mk-faint text-[13px]">Aurora vs</span>
              <span className="-mt-4 text-2xl font-semibold tracking-tight text-white">
                {item.versus}
              </span>
              <p className="text-mk-muted text-[15px] leading-relaxed">
                {item.body}
              </p>
              <div className="mt-auto border-t border-white/[0.06] pt-5">
                <span className="hud-label text-hud-gold text-[10px]">
                  The trade
                </span>
                <p className="mt-2 text-[15px] leading-relaxed text-white">
                  {item.trade}
                </p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </Container>
  </Section>
);
