import type { TocEntry } from "./toc";

const TocList = ({ entries }: { entries: readonly TocEntry[] }) => (
  <ol className="flex flex-col gap-2.5 text-[14px] leading-snug">
    {entries.map((entry) => (
      <li key={entry.id}>
        <a
          href={`#${entry.id}`}
          className="text-mk-faint block transition-colors hover:text-white"
        >
          {entry.title}
        </a>
      </li>
    ))}
  </ol>
);

/**
 * The walk's sections. `rail` is the sticky column beside the text on wide screens; `inline`
 * is a collapsed list above the text for everything narrower.
 */
export const WalkToc = ({
  entries,
  variant,
}: {
  entries: readonly TocEntry[];
  variant: "inline" | "rail";
}) =>
  variant === "rail" ? (
    <nav aria-label="In this walk" className="sticky top-28">
      <p className="mb-4 text-[12px] font-medium tracking-[0.14em] text-white/50 uppercase">
        In this walk
      </p>
      <TocList entries={entries} />
    </nav>
  ) : (
    <nav aria-label="In this walk" data-testid="walk-toc">
      <details className="group rounded-2xl border border-white/[0.08] bg-white/[0.02] px-5 py-4">
        <summary className="flex cursor-pointer list-none items-center justify-between text-[13px] font-medium tracking-[0.1em] text-white/80 uppercase [&::-webkit-details-marker]:hidden">
          In this walk
          <span className="text-mk-faint text-[13px] tracking-normal normal-case">
            {entries.length} sections
          </span>
        </summary>
        <div className="mt-4 border-t border-white/[0.06] pt-4">
          <TocList entries={entries} />
        </div>
      </details>
    </nav>
  );
