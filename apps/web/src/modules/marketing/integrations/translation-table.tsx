import { ArrowUpRight, Search } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import {
  translationCallouts,
  translationTools,
} from "~/modules/marketing/content/integrations";
import { links } from "~/modules/marketing/content/site";

interface TranslationTableProps {
  readonly tool: string;
  readonly query?: string;
  readonly basePath: string;
  readonly limit?: number;
  readonly showPicker?: boolean;
  readonly showAllHref?: string;
}

/**
 * "Their term vs Aurora" from the docs' "In other agent tools" callouts.
 * Server-rendered and filtered by URL params, so none of the data ships to the browser.
 */
export const TranslationTable = ({
  tool,
  query = "",
  basePath,
  limit,
  showPicker = true,
  showAllHref,
}: TranslationTableProps) => {
  const needle = query.trim().toLowerCase();
  const matches = translationCallouts
    .map((callout) => ({
      ...callout,
      rows: callout.rows.filter(
        (row) =>
          row.links[tool] &&
          (!needle ||
            [callout.concept, row.term, row.meaning, callout.differs].some(
              (text) => text.toLowerCase().includes(needle),
            )),
      ),
    }))
    .filter((callout) => callout.rows.length > 0);
  const shown = limit ? matches.slice(0, limit) : matches;
  const rowCount = matches.reduce(
    (total, callout) => total + callout.rows.length,
    0,
  );

  return (
    <div data-testid="translation-table" className="flex flex-col gap-6">
      {showPicker && (
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <nav className="flex flex-wrap gap-1.5" aria-label="Agent tool">
            {translationTools.map((item) => (
              <Link
                key={item}
                scroll={false}
                href={`${basePath}?tool=${encodeURIComponent(item)}${needle ? `&q=${encodeURIComponent(query)}` : ""}#translations`}
                aria-current={item === tool ? "true" : undefined}
                className={cn(
                  "h-8 rounded-full border px-3 text-[13px] leading-8 transition-colors",
                  item === tool
                    ? "border-hud-cyan/40 bg-hud-cyan/10 text-hud-cyan"
                    : "border-white/[0.08] text-white/60 hover:text-white",
                )}
              >
                {item}
              </Link>
            ))}
          </nav>
          <form
            action={`${basePath}#translations`}
            className="relative w-full lg:w-72"
          >
            <input type="hidden" name="tool" value={tool} />
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-white/55" />
            <input
              type="search"
              name="q"
              defaultValue={query}
              placeholder="Filter terms"
              aria-label="Filter terms"
              className="h-10 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] pr-3 pl-9 text-[14px] text-white placeholder:text-white/50 focus:border-white/20 focus:outline-none"
            />
          </form>
        </div>
      )}

      <p className="text-mk-faint text-[13px]" data-testid="translation-count">
        {rowCount} terms from {tool} across {matches.length} Aurora concepts
        {needle ? ` matching "${query}"` : ""}.
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        {shown.map((callout, calloutIndex) => (
          <article
            key={`${callout.doc}-${callout.concept}-${calloutIndex}`}
            className="mk-card flex flex-col gap-4 p-6"
          >
            <header className="flex items-start justify-between gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-mk-faint text-[12px]">
                  Aurora concept
                </span>
                <span className="text-[18px] font-medium text-white">
                  {callout.concept}
                </span>
              </div>
              <a
                href={links.doc(callout.doc)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-mk-faint flex shrink-0 items-center gap-1 font-mono text-[10.5px] hover:text-white"
              >
                docs/{callout.doc} <ArrowUpRight className="size-3" />
              </a>
            </header>
            <ul className="flex flex-col gap-3">
              {callout.rows.map((row, rowIndex) => (
                <li
                  key={`${row.term}-${rowIndex}`}
                  className="flex flex-col gap-1 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
                >
                  <span className="flex items-center justify-between gap-3">
                    <a
                      href={row.links[tool]}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[15px] font-medium text-white underline-offset-4 hover:underline"
                    >
                      {row.term}
                    </a>
                    <span
                      className={cn(
                        "font-hud shrink-0 rounded-sm border px-1.5 py-0.5 text-[9.5px] font-semibold tracking-[0.12em] uppercase",
                        row.same
                          ? "border-hud-cyan/30 text-hud-cyan"
                          : "border-hud-gold/30 text-hud-gold",
                      )}
                    >
                      {row.same ? "Close match" : "Not the same"}
                    </span>
                  </span>
                  <span className="text-mk-muted text-[14px] leading-relaxed">
                    {row.meaning.replace(/^Not the same:\s*/, "")}
                  </span>
                </li>
              ))}
            </ul>
            <p className="border-hud-gold/40 border-l-2 pl-3 text-[14px] leading-relaxed text-white/80">
              <span className="text-hud-gold font-medium">
                How Aurora differs:{" "}
              </span>
              {callout.differs}
            </p>
          </article>
        ))}
      </div>

      {showAllHref && shown.length < matches.length && (
        <Link
          href={showAllHref}
          scroll={false}
          data-testid="translation-show-all"
          className="mx-auto inline-flex h-10 items-center rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 text-[14px] font-medium text-white hover:bg-white/[0.1]"
        >
          Show all {matches.length} concepts
        </Link>
      )}
    </div>
  );
};
