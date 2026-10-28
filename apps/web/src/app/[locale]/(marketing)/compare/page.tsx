import { Check, Minus, X } from "lucide-react";

import { cn } from "@akashic-labs/ui";

import { getMetadata } from "~/lib/metadata";
import { links, routes } from "~/modules/marketing/content/site";
import { tradeOffs } from "~/modules/marketing/home/trade-offs";
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
  title: "Compare: Aurora vs memory APIs, rules files and chat history",
  description:
    "How Aurora differs from hosted memory APIs, CLAUDE.md and AGENTS.md rules files, and saved chat history. An honest comparison, including where Aurora is the wrong choice.",
  canonical: routes.compare,
});

/** "yes", "no", "partial", or a short phrase shown as text. */
type Mark = string;

const approaches = [
  "Aurora",
  "Hosted memory API",
  "Rules files",
  "Chat history",
] as const;

const rows: { label: string; values: [Mark, Mark, Mark, Mark] }[] = [
  {
    label: "Where it lives",
    values: ["Your disk", "Their cloud", "Your repo", "Your disk"],
  },
  {
    label: "Reaches the agent",
    values: [
      "Right before the action",
      "When the agent asks",
      "Every session, in bulk",
      "When someone rereads it",
    ],
  },
  {
    label: "Shared across harnesses",
    values: ["yes", "partial", "partial", "no"],
  },
  {
    label: "Stays silent when nothing fits",
    values: ["yes", "partial", "no", "no"],
  },
  { label: "Knows which advice helped", values: ["yes", "no", "no", "no"] },
  {
    label: "Agent mail, locks and handoffs",
    values: ["yes", "no", "no", "no"],
  },
  {
    label: "History never rewritten",
    values: ["yes", "partial", "partial", "yes"],
  },
  {
    label: "LLM in the retrieval path",
    values: ["None", "Usually", "None", "None"],
  },
  {
    label: "Semantic search over meaning",
    values: ["Optional, off", "yes", "no", "no"],
  },
  { label: "Hosted with an SLA", values: ["no", "yes", "no", "no"] },
];

const MarkCell = ({
  value,
  highlight,
}: {
  value: Mark;
  highlight: boolean;
}) => {
  if (value === "yes")
    return (
      <Check
        className={cn(
          "mx-auto size-4",
          highlight ? "text-hud-cyan" : "text-white/70",
        )}
        aria-label="Yes"
      />
    );
  if (value === "no")
    return <X className="mx-auto size-4 text-white/45" aria-label="No" />;
  if (value === "partial")
    return (
      <Minus className="text-hud-gold/80 mx-auto size-4" aria-label="Partly" />
    );
  return (
    <span
      className={cn(
        "text-[13.5px]",
        highlight ? "text-white" : "text-mk-muted",
      )}
    >
      {value}
    </span>
  );
};

const fileStrengths = [
  "Repo facts that rarely change: build commands, style rules, layout",
  "Instructions every agent should read on every run",
  "Things a person wants to review in a pull request",
];

const fileLimits = [
  {
    need: "A fix found mid-session",
    files: "Someone has to edit the file",
    aurora: "aurora learn, in the moment",
  },
  {
    need: "The one line that matters now",
    files: "Buried among every other line",
    aurora: "At most three, right before the action",
  },
  {
    need: "Knowing a rule helped",
    files: "No signal",
    aurora: "Flip credit when a fail turns into a pass",
  },
  {
    need: "Retiring stale advice",
    files: "Manual cleanup",
    aurora: "Idle lessons get benched, never deleted",
  },
  {
    need: "Two agents, one file",
    files: "Out of scope",
    aurora: "Short advisory locks",
  },
];

export default function ComparePage() {
  return (
    <>
      <PageHero
        eyebrow="Compare"
        title={
          <>
            Aurora vs the usual ways
            <span className="text-mk-muted"> to give agents memory</span>
          </>
        }
        description="Hosted memory APIs, rules files and saved chats all help. Here is where each one shines, where Aurora differs, and when Aurora is the wrong pick."
      />

      <Section id="memory-apis" className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <Reveal>
            <div
              data-testid="compare-table"
              className="overflow-x-auto rounded-[22px] border border-white/[0.08]"
            >
              <table className="w-full min-w-[820px] text-center text-[14px]">
                <thead>
                  <tr className="text-[13px]">
                    <th className="w-[26%] px-6 py-4 text-left font-medium text-white/50">
                      Capability
                    </th>
                    {approaches.map((approach, index) => (
                      <th
                        key={approach}
                        className={cn(
                          "px-4 py-4 font-medium",
                          index === 0
                            ? "bg-hud-cyan/[0.06] text-hud-cyan"
                            : "text-white/70",
                        )}
                      >
                        {approach}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {rows.map((row) => (
                    <tr key={row.label}>
                      <td className="px-6 py-4 text-left text-white/85">
                        {row.label}
                      </td>
                      {row.values.map((value, index) => (
                        <td
                          key={`${row.label}-${index}`}
                          className={cn(
                            "px-4 py-4",
                            index === 0 && "bg-hud-cyan/[0.04]",
                          )}
                        >
                          <MarkCell value={value} highlight={index === 0} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-mk-faint border-t border-white/[0.06] px-6 py-3 text-left text-[12.5px]">
                Columns describe each approach in general, not one vendor. A
                dash means it depends on the product. Aurora facts come from its
                docs. Last reviewed October 2026.
              </p>
            </div>
          </Reveal>
        </Container>
      </Section>

      <Section backdrop="nebula" id="rules-files">
        <Container>
          <SectionIntro
            eyebrow="Aurora vs rules files"
            title="Files first, then memory"
            description="CLAUDE.md and AGENTS.md are the right home for facts that rarely change. Aurora's own AGENTS.md is a normal one that tells each agent to boot, learn and recall. Keep your files. Add memory for what files cannot hold."
          />
          <div className="mt-12 grid gap-6 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
            <div className="mk-card flex flex-col gap-4 p-7">
              <HudLabel tone="cyan">Files are great for</HudLabel>
              <ul className="flex flex-col gap-3">
                {fileStrengths.map((item) => (
                  <li
                    key={item}
                    className="flex gap-3 text-[15px] text-white/85"
                  >
                    <Check className="text-hud-cyan mt-1 size-4 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="overflow-x-auto rounded-[22px] border border-white/[0.08]">
              <table className="w-full min-w-[560px] text-left text-[14.5px]">
                <thead className="text-mk-faint bg-white/[0.02] text-[12px]">
                  <tr>
                    <th className="px-5 py-3 font-medium">
                      What files can&apos;t hold
                    </th>
                    <th className="px-5 py-3 font-medium">With a rules file</th>
                    <th className="px-5 py-3 font-medium">With Aurora</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {fileLimits.map((row) => (
                    <tr key={row.need}>
                      <td className="px-5 py-4 font-medium text-white">
                        {row.need}
                      </td>
                      <td className="text-mk-faint px-5 py-4">{row.files}</td>
                      <td className="px-5 py-4 text-white/85">{row.aurora}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Container>
      </Section>

      <Section id="chat-history">
        <Container className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <SectionIntro
            eyebrow="Aurora vs chat history"
            title="A transcript is a record, not a memory"
            description="Saved chats keep everything and surface nothing. Aurora indexes every transcript so you can find and cite what was said, then carries the parts that matter forward as handoffs and lessons. Nobody rereads yesterday's chat."
          />
          <HudFrame tone="cyan">
            <div className="flex flex-col gap-3 p-7 font-mono text-[12.5px]">
              <HudLabel tone="cyan">Find it, cite it</HudLabel>
              <div className="text-white">
                <span className="text-hud-cyan">$ </span>aurora eye find
                &quot;embedded redis&quot; --who operator
              </div>
              <div className="text-white/45">
                # each hit has an address like &lt;session&gt;:&lt;line&gt;
              </div>
              <div className="text-white">
                <span className="text-hud-cyan">$ </span>aurora eye get
                &lt;session&gt;:&lt;line&gt;
              </div>
              <div className="text-white/45">
                # the verbatim record. No model rewrites it on the way.
              </div>
            </div>
          </HudFrame>
        </Container>
      </Section>

      <Section backdrop="caustics">
        <Container>
          <SectionIntro
            eyebrow="The trade"
            title="Every option costs something"
          />
          <div className="mt-12 grid gap-4 lg:grid-cols-3">
            {tradeOffs.map((item) => (
              <div
                key={item.versus}
                className="mk-card flex flex-col gap-4 p-7"
              >
                <span className="text-[20px] font-semibold tracking-tight text-white">
                  vs {item.versus}
                </span>
                <p className="text-mk-muted text-[15px] leading-relaxed">
                  {item.body}
                </p>
                <p className="mt-auto border-t border-white/[0.06] pt-4 text-[15px] text-white">
                  {item.trade}
                </p>
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
                <HudLabel>Why trust this page?</HudLabel>
                <h2 className="mk-title text-3xl sm:text-4xl">
                  You don&apos;t have to.
                </h2>
                <p className="text-mk-muted max-w-2xl text-[16px] leading-relaxed">
                  Every Aurora claim here links back to its docs, and the source
                  is open. Read the decision records, run the sandbox, and check
                  for yourself. If a hosted API fits you better, use it.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <ButtonLink href={routes.evidence} variant="secondary" arrow>
                  See the evidence
                </ButtonLink>
                <ButtonLink
                  href={links.doc("how-to/try-it-in-a-sandbox")}
                  arrow
                >
                  Try the sandbox
                </ButtonLink>
              </div>
            </div>
          </HudFrame>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
