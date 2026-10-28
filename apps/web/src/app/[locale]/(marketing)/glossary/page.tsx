import { getMetadata } from "~/lib/metadata";
import { glossary } from "~/modules/marketing/content/aurora";
import { links, routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import { Container, Section } from "~/modules/marketing/ui/primitives";

export const generateMetadata = getMetadata({
  title: "Glossary",
  description:
    "Every Aurora term in one sentence: lessons, recall at action, flip credit, the bus, seats, handoffs and more.",
  canonical: routes.glossary,
});

const anchor = (term: string) =>
  term
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

export default function GlossaryPage() {
  const sorted = [...glossary].sort((a, b) => a.term.localeCompare(b.term));
  const letters = [
    ...new Set(sorted.map((item) => item.term[0]?.toUpperCase() ?? "")),
  ];

  return (
    <>
      <PageHero
        eyebrow="Glossary"
        title={
          <>
            Every term
            <span className="text-mk-muted"> in one sentence</span>
          </>
        }
        description="One vocabulary, and names must not lie. These are the words you will meet in Aurora and its docs."
      >
        <nav aria-label="Letters" className="flex flex-wrap gap-1.5">
          {letters.map((letter) => (
            <a
              key={letter}
              href={`#letter-${letter}`}
              className="font-hud flex size-9 items-center justify-center rounded-lg border border-white/[0.08] text-[14px] font-semibold text-white/70 hover:border-white/20 hover:text-white"
            >
              {letter}
            </a>
          ))}
        </nav>
      </PageHero>

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          {letters.map((letter) => (
            <section
              key={letter}
              id={`letter-${letter}`}
              className="grid scroll-mt-28 gap-4 border-t border-white/[0.07] py-10 md:grid-cols-[120px_1fr]"
            >
              <span className="font-hud text-hud-gold text-4xl font-semibold">
                {letter}
              </span>
              <dl className="grid gap-x-10 gap-y-6 sm:grid-cols-2">
                {sorted
                  .filter((item) => item.term[0]?.toUpperCase() === letter)
                  .map((item) => (
                    <div
                      key={item.term}
                      id={anchor(item.term)}
                      data-testid="glossary-term"
                      className="scroll-mt-28"
                    >
                      <dt className="text-[17px] font-medium text-white">
                        {item.term}
                      </dt>
                      <dd className="text-mk-muted mt-1 text-[15px] leading-relaxed">
                        {item.definition}{" "}
                        {item.doc && (
                          <a
                            href={links.doc(item.doc)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-mk-faint font-mono text-[11px] hover:text-white"
                          >
                            docs
                          </a>
                        )}
                      </dd>
                    </div>
                  ))}
              </dl>
            </section>
          ))}
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
