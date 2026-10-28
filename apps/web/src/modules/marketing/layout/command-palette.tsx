"use client";

import { ArrowUpRight, CornerDownLeft, Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { cn } from "@akashic-labs/ui";

import type { ReactNode } from "react";
import type { SearchEntry } from "~/modules/marketing/content/search-index";

const PaletteContext = createContext<{ open: () => void }>({
  open: () => undefined,
});

export const usePalette = () => useContext(PaletteContext);

const GROUP_ORDER: SearchEntry["group"][] = [
  "Pages",
  "Aurora",
  "Concepts",
  "Docs",
  "Glossary",
  "Blog",
];
const MAX_RESULTS = 40;

const score = (entry: SearchEntry, tokens: string[]) => {
  const title = entry.title.toLowerCase();
  const haystack =
    `${title} ${entry.description} ${entry.keywords ?? ""}`.toLowerCase();
  if (!tokens.every((token) => haystack.includes(token))) return -1;
  let value = 0;
  for (const token of tokens) {
    if (title.startsWith(token)) value += 6;
    else if (title.includes(token)) value += 3;
    else value += 1;
  }
  return value - title.length * 0.01;
};

/** ⌘K palette: search every page, pillar, concept, doc, glossary term and post. */
export const CommandPaletteProvider = ({
  index,
  children,
}: {
  index: SearchEntry[];
  children: ReactNode;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => {
    setIsOpen(false);
    setQuery("");
    setActive(0);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const typing = (event.target as HTMLElement | null)?.closest(
        "input, textarea, [contenteditable]",
      );
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setIsOpen((value) => !value);
      } else if (event.key === "/" && !typing && !isOpen) {
        event.preventDefault();
        setIsOpen(true);
      } else if (event.key === "Escape" && isOpen) {
        // Works even before focus has moved into the search field.
        close();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, close]);

  useEffect(() => {
    if (isOpen) requestAnimationFrame(() => inputRef.current?.focus());
  }, [isOpen]);

  const results = useMemo(() => {
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    const scored = tokens.length
      ? index
          .map((entry) => ({ entry, value: score(entry, tokens) }))
          .filter((item) => item.value >= 0)
          .sort((a, b) => b.value - a.value)
          .map((item) => item.entry)
      : index.filter(
          (entry) => entry.group === "Pages" || entry.group === "Aurora",
        );
    const limited = scored.slice(0, MAX_RESULTS);
    return GROUP_ORDER.flatMap((group) =>
      limited.filter((entry) => entry.group === group),
    );
  }, [index, query]);

  useEffect(() => setActive(0), [query]);

  useEffect(() => {
    listRef.current
      ?.querySelector(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const go = (entry: SearchEntry | undefined) => {
    if (!entry) return;
    close();
    if (entry.href.startsWith("http"))
      window.open(entry.href, "_blank", "noopener,noreferrer");
    else router.push(entry.href);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((value) => Math.min(results.length - 1, value + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((value) => Math.max(0, value - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(results[active]);
    } else if (event.key === "Escape") {
      close();
    }
  };

  let lastGroup: string | null = null;

  return (
    <PaletteContext.Provider value={{ open }}>
      {children}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-0 z-[60] flex items-start justify-center bg-black/60 px-4 pt-[12vh] backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onMouseDown={(event) =>
              event.target === event.currentTarget && close()
            }
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Search the site"
              data-testid="command-palette"
              initial={{ opacity: 0, y: -12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-[640px] overflow-hidden rounded-2xl border border-white/[0.1] bg-[#0b0b0d]/95 shadow-[0_40px_120px_-20px_rgb(0_0_0/0.9),0_0_0_1px_rgb(10_200_185/0.08)] backdrop-blur-xl"
              onKeyDown={onKeyDown}
            >
              <div className="flex items-center gap-3 border-b border-white/[0.07] px-4">
                <Search className="size-4 text-white/55" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search pages, concepts, docs and terms"
                  aria-label="Search"
                  aria-controls="palette-results"
                  aria-activedescendant={
                    results[active] ? `palette-${active}` : undefined
                  }
                  className="h-14 flex-1 bg-transparent text-[15px] text-white placeholder:text-white/50 focus:outline-none"
                />
                <kbd className="rounded border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-white/55">
                  esc
                </kbd>
              </div>
              <div
                ref={listRef}
                id="palette-results"
                role="listbox"
                className="max-h-[52vh] overflow-y-auto p-2"
              >
                {results.length === 0 && (
                  <p className="px-3 py-10 text-center text-[14px] text-white/45">
                    Nothing matches &ldquo;{query}&rdquo;. Try fewer words.
                  </p>
                )}
                {results.map((entry, resultIndex) => {
                  const header = entry.group !== lastGroup ? entry.group : null;
                  lastGroup = entry.group;
                  const external = entry.href.startsWith("http");
                  return (
                    <div key={`${entry.group}-${entry.href}-${entry.title}`}>
                      {header && (
                        <div className="hud-label px-3 pt-3 pb-1.5 text-[9.5px] text-white/50">
                          {header}
                        </div>
                      )}
                      <button
                        type="button"
                        role="option"
                        id={`palette-${resultIndex}`}
                        data-index={resultIndex}
                        aria-selected={resultIndex === active}
                        onMouseMove={() => setActive(resultIndex)}
                        onClick={() => go(entry)}
                        className={cn(
                          "flex w-full items-center justify-between gap-4 rounded-lg px-3 py-2.5 text-left transition-colors",
                          resultIndex === active
                            ? "bg-white/[0.07]"
                            : "hover:bg-white/[0.04]",
                        )}
                      >
                        <span className="flex min-w-0 flex-col">
                          <span className="truncate text-[14px] text-white">
                            {entry.title}
                          </span>
                          {entry.description && (
                            <span className="truncate text-[12.5px] text-white/45">
                              {entry.description}
                            </span>
                          )}
                        </span>
                        {resultIndex === active &&
                          (external ? (
                            <ArrowUpRight className="text-hud-cyan size-4 shrink-0" />
                          ) : (
                            <CornerDownLeft className="text-hud-cyan size-4 shrink-0" />
                          ))}
                      </button>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-between border-t border-white/[0.07] px-4 py-2.5 text-[11.5px] text-white/50">
                <span>
                  <kbd className="font-mono">↑↓</kbd> to move ·{" "}
                  <kbd className="font-mono">↵</kbd> to open
                </span>
                <span>{index.length} entries</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PaletteContext.Provider>
  );
};

export const SearchTrigger = ({ className }: { className?: string }) => {
  const { open } = usePalette();
  return (
    <button
      type="button"
      onClick={open}
      aria-label="Search the site"
      data-testid="search-trigger"
      className={cn(
        "flex h-8 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] pr-1.5 pl-2.5 text-[13px] text-white/55 transition-colors hover:border-white/15 hover:text-white",
        className,
      )}
    >
      <Search className="size-3.5" />
      <span className="hidden xl:inline">Search</span>
      <kbd className="rounded border border-white/10 px-1 font-mono text-[10px] text-white/55">
        ⌘K
      </kbd>
    </button>
  );
};
