"use client";

import { RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@akashic-labs/ui";

import {
  createState,
  run,
  SUGGESTIONS,
} from "~/modules/marketing/playground/engine";
import { HudLabel } from "~/modules/marketing/ui/hud";

import type {
  OutputLine,
  PlaygroundState,
} from "~/modules/marketing/playground/engine";

interface Entry {
  readonly id: number;
  readonly command?: string;
  readonly lines: OutputLine[];
}

const lineStyles: Record<OutputLine["kind"], string> = {
  out: "text-white/75",
  dim: "text-white/55",
  ok: "text-hud-cyan",
  gold: "text-hud-gold",
  err: "text-hud-red",
};

const INTRO: OutputLine[] = [
  {
    kind: "dim",
    text: "# Aurora playground. Two lessons are already in the record.",
  },
  {
    kind: "dim",
    text: "# Learn one, recall it against a file, then try a file it does not fit.",
  },
];

/** Type real Aurora commands against an in-browser model of the CLI. */
export const Playground = () => {
  const state = useRef<PlaygroundState>(createState());
  const [entries, setEntries] = useState<Entry[]>([{ id: 0, lines: INTRO }]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [cursor, setCursor] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [entries]);

  const submit = (command: string) => {
    const trimmed = command.trim();
    if (!trimmed) return;
    if (trimmed === "clear") {
      setEntries([]);
    } else {
      const lines = run(state.current, trimmed);
      setEntries((current) => [
        ...current,
        { id: nextId.current++, command: trimmed, lines },
      ]);
    }
    setHistory((current) =>
      [trimmed, ...current.filter((item) => item !== trimmed)].slice(0, 30),
    );
    setCursor(-1);
    setInput("");
  };

  const reset = () => {
    state.current = createState();
    setEntries([{ id: nextId.current++, lines: INTRO }]);
    setInput("");
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      submit(input);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      const next = Math.min(history.length - 1, cursor + 1);
      if (history[next]) {
        setCursor(next);
        setInput(history[next]);
      }
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      const next = cursor - 1;
      setCursor(Math.max(-1, next));
      setInput(next >= 0 ? (history[next] ?? "") : "");
    } else if (event.key === "Tab") {
      event.preventDefault();
      const match = SUGGESTIONS.find(
        (item) => item.startsWith(input) && item !== input,
      );
      if (input && match) setInput(match);
    } else if (event.key === "l" && event.ctrlKey) {
      event.preventDefault();
      setEntries([]);
    }
  };

  return (
    <div data-testid="playground" className="mk-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="text-mk-faint ml-2 font-mono text-[11px]">
            aurora · playground
          </span>
        </div>
        <div className="flex items-center gap-3">
          <HudLabel tone="cyan" className="hidden text-[9.5px] sm:inline">
            Simulated · real output formats
          </HudLabel>
          <button
            type="button"
            onClick={reset}
            className="text-mk-faint flex items-center gap-1 text-[12px] hover:text-white"
            aria-label="Reset the playground"
          >
            <RotateCcw className="size-3.5" /> Reset
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        onClick={() => inputRef.current?.focus()}
        className="h-[360px] cursor-text overflow-y-auto bg-[#07080a] p-4 font-mono text-[12.5px] leading-6 sm:p-5"
      >
        {entries.map((entry) => (
          <div key={entry.id} className="mb-1">
            {entry.command && (
              <div className="text-white">
                <span className="text-hud-cyan select-none">$ </span>
                {entry.command}
              </div>
            )}
            {entry.lines.map((line, index) => (
              <div
                key={index}
                className={cn(
                  "break-words whitespace-pre-wrap",
                  lineStyles[line.kind],
                )}
              >
                {line.text}
              </div>
            ))}
          </div>
        ))}
        <div className="flex items-center">
          <span className="text-hud-cyan select-none">$&nbsp;</span>
          <input
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            aria-label="Aurora command"
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            className="caret-hud-cyan flex-1 bg-transparent text-white focus:outline-none"
            placeholder="type help"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 border-t border-white/[0.06] p-3">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => submit(suggestion)}
            className="max-w-full truncate rounded-full border border-white/[0.08] px-3 py-1 font-mono text-[11px] text-white/60 transition-colors hover:border-white/20 hover:text-white"
            title={suggestion}
          >
            {suggestion.length > 58
              ? `${suggestion.slice(0, 56)}…`
              : suggestion}
          </button>
        ))}
      </div>
    </div>
  );
};
