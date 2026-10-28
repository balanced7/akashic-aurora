import { harnesses } from "~/modules/marketing/content/aurora";
import { Container } from "~/modules/marketing/ui/primitives";

const names = harnesses
  .filter((item) => item.kind !== "runtime")
  .map((item) => item.name);

export const HarnessStrip = () => (
  <section
    aria-label="Works with"
    className="border-y border-white/[0.06] py-10"
  >
    <Container className="flex flex-col items-center gap-6 md:flex-row md:gap-10">
      <p className="text-mk-faint shrink-0 text-sm md:max-w-[200px]">
        One memory for the agents you already run
      </p>
      <div className="mk-fade-x relative w-full overflow-hidden">
        <div className="animate-mk-marquee flex w-max gap-12 pr-12 hover:[animation-play-state:paused]">
          {[...names, ...names].map((name, index) => (
            <span
              key={`${name}-${index}`}
              className="text-[22px] font-semibold tracking-[-0.03em] whitespace-nowrap text-white/45 transition-colors hover:text-white"
              aria-hidden={index >= names.length}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </Container>
  </section>
);
