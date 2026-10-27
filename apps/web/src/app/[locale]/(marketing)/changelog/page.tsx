import { GitCommitHorizontal, Link2 } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { getMetadata } from "~/lib/metadata";
import { changelog } from "~/modules/marketing/content/changelog";
import history from "~/modules/marketing/content/generated/aurora-history.json";
import { links, routes } from "~/modules/marketing/content/site";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
} from "~/modules/marketing/ui/primitives";

import type { ChangelogEntry } from "~/modules/marketing/content/changelog";

export const generateMetadata = getMetadata({
  title: "Changelog",
  description:
    "What shipped in Aurora, month by month, with the commits that prove it.",
  canonical: routes.changelog,
});

const areas: ChangelogEntry["area"][] = [
  "Memory",
  "Bifrost",
  "Coordination",
  "Story",
  "Foundations",
  "Method",
  "Tools",
  "Docs",
  "Setup",
];

const monthLabel = (month: string) =>
  new Date(`${month}-01T00:00:00Z`).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

export default async function ChangelogPage(props: {
  searchParams: Promise<{ area?: string }>;
}) {
  const { area } = await props.searchParams;
  const activeArea = areas.find((item) => item === area);
  const months = changelog
    .map((month) => ({
      ...month,
      entries: activeArea
        ? month.entries.filter((entry) => entry.area === activeArea)
        : month.entries,
    }))
    .filter((month) => month.entries.length > 0);
  const commitsByMonth = new Map(
    history.months.map((month) => [month.month, month.total]),
  );
  const maxCommits = Math.max(...history.months.map((month) => month.total));

  return (
    <>
      <PageHero
        backdrop="network"
        eyebrow="Changelog"
        title={
          <>
            What shipped,
            <span className="text-mk-muted"> month by month</span>
          </>
        }
        description={`${history.totalCommits.toLocaleString("en-US")} commits since ${history.firstCommit}. Every entry below links to the commits that prove it.`}
        actions={
          <ButtonLink href={links.commits} variant="secondary" arrow>
            Full commit history
          </ButtonLink>
        }
      >
        <div
          data-testid="changelog-activity"
          className="mk-card flex flex-col gap-4 p-6"
        >
          <HudLabel tone="muted">Commits per month</HudLabel>
          <div className="flex h-32 items-end gap-3">
            {[...history.months].reverse().map((month) => (
              <a
                key={month.month}
                href={`#m-${month.month}`}
                className="group flex flex-1 flex-col items-center gap-2"
              >
                <span className="font-hud text-[11px] text-white/50 tabular-nums group-hover:text-white">
                  {month.total}
                </span>
                <span
                  className="from-hud-cyan-deep to-hud-cyan w-full rounded-t-md bg-gradient-to-t opacity-80 transition-opacity group-hover:opacity-100"
                  style={{
                    height: `${Math.max(4, (month.total / maxCommits) * 88)}px`,
                  }}
                />
                <span className="text-mk-faint text-[11px]">
                  {new Date(`${month.month}-01T00:00:00Z`).toLocaleString(
                    "en-US",
                    { month: "short", timeZone: "UTC" },
                  )}
                </span>
              </a>
            ))}
          </div>
        </div>
      </PageHero>

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container>
          <nav
            aria-label="Filter by area"
            className="mb-12 flex flex-wrap gap-1.5"
          >
            <Link
              href={routes.changelog}
              scroll={false}
              aria-current={!activeArea ? "true" : undefined}
              className={cn(
                "h-8 rounded-full border px-3 text-[13px] leading-8",
                !activeArea
                  ? "border-hud-cyan/40 bg-hud-cyan/10 text-hud-cyan"
                  : "border-white/[0.08] text-white/60 hover:text-white",
              )}
            >
              All
            </Link>
            {areas.map((item) => (
              <Link
                key={item}
                href={`${routes.changelog}?area=${item}`}
                scroll={false}
                aria-current={activeArea === item ? "true" : undefined}
                className={cn(
                  "h-8 rounded-full border px-3 text-[13px] leading-8",
                  activeArea === item
                    ? "border-hud-cyan/40 bg-hud-cyan/10 text-hud-cyan"
                    : "border-white/[0.08] text-white/60 hover:text-white",
                )}
              >
                {item}
              </Link>
            ))}
          </nav>

          <div className="flex flex-col">
            {months.map((month) => (
              <section
                key={month.month}
                id={`m-${month.month}`}
                data-testid="changelog-month"
                className="grid scroll-mt-28 gap-6 border-t border-white/[0.07] py-12 lg:grid-cols-[260px_minmax(0,1fr)] lg:gap-12"
              >
                <header className="flex flex-col gap-3 lg:sticky lg:top-28 lg:self-start">
                  <a
                    href={`#m-${month.month}`}
                    className="group flex items-center gap-2"
                  >
                    <span className="font-hud text-hud-gold text-[13px] font-semibold tracking-[0.14em] uppercase">
                      {monthLabel(month.month)}
                    </span>
                    <Link2 className="size-3.5 text-white/0 transition-colors group-hover:text-white/50" />
                  </a>
                  <h2 className="text-[24px] leading-tight font-semibold tracking-tight text-white">
                    {month.title}
                  </h2>
                  <p className="text-mk-muted text-[14.5px] leading-relaxed">
                    {month.summary}
                  </p>
                  <span className="text-mk-faint font-mono text-[11px]">
                    {commitsByMonth.get(month.month)?.toLocaleString("en-US") ??
                      0}{" "}
                    commits
                  </span>
                </header>
                <div className="grid gap-3 sm:grid-cols-2">
                  {month.entries.map((entry) => (
                    <article
                      key={entry.title}
                      className="mk-card flex flex-col gap-3 p-5"
                    >
                      <span className="hud-label text-hud-cyan text-[9.5px]">
                        {entry.area}
                      </span>
                      <h3 className="text-[16.5px] font-medium tracking-tight text-white">
                        {entry.title}
                      </h3>
                      <p className="text-mk-muted text-[14px] leading-relaxed">
                        {entry.body}
                      </p>
                      <div className="mt-auto flex flex-wrap gap-1.5 pt-1">
                        {entry.commits.map((sha) => (
                          <a
                            key={sha}
                            href={`${links.repo}/commit/${sha}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-mk-faint inline-flex items-center gap-1 rounded-md border border-white/[0.06] px-1.5 py-0.5 font-mono text-[10.5px] hover:text-white"
                          >
                            <GitCommitHorizontal className="size-3" />
                            {sha.slice(0, 7)}
                          </a>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </Container>
      </Section>

      <CtaBand />
    </>
  );
}
