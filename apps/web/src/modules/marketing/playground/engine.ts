/**
 * A tiny in-browser model of the Aurora CLI for the playground.
 * Output formats copy real output captured from a sandboxed Aurora run (see content/aurora.ts).
 * Matching is word overlap with a floor, like recall: no model, and silence when nothing fits.
 */

import { liveNumbers } from "~/modules/marketing/content/aurora";

export interface Lesson {
  readonly name: string;
  readonly agent: string;
  readonly recommend: string;
  readonly success: "true" | "partial" | "false";
  helped: number;
}

export interface PlaygroundState {
  readonly lessons: Lesson[];
  readonly locks: Map<string, string>;
  readonly agent: string;
}

export type OutputKind = "out" | "dim" | "ok" | "gold" | "err";

export interface OutputLine {
  readonly kind: OutputKind;
  readonly text: string;
}

export const createState = (): PlaygroundState => ({
  agent: "me",
  locks: new Map(),
  lessons: [
    {
      name: "port-clash",
      agent: "claude",
      recommend:
        "Use when a test run hangs at start, before you retry: check the port first.",
      success: "partial",
      helped: 2,
    },
    {
      name: "pytest-redis-db",
      agent: "codex",
      recommend: "Use when pytest touches Redis: point it at db 15 only.",
      success: "true",
      helped: 0,
    },
  ],
});

const STOP_WORDS = new Set([
  "the",
  "a",
  "an",
  "to",
  "of",
  "and",
  "or",
  "when",
  "use",
  "before",
  "you",
  "it",
  "at",
  "on",
  "in",
  "for",
  "is",
]);

const tokenize = (text: string) =>
  text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 2 && !STOP_WORDS.has(word));

/** Share of query words found in the lesson, the same shape as recall's minimum match. */
const relevance = (lesson: Lesson, query: string) => {
  const words = tokenize(query);
  if (words.length === 0) return 0;
  const haystack = new Set(tokenize(`${lesson.name} ${lesson.recommend}`));
  const hits = words.filter(
    (word) =>
      haystack.has(word) || [...haystack].some((item) => item.startsWith(word)),
  ).length;
  return hits / words.length;
};

const FLOOR = 0.2;

/** Split a command line into words, keeping quoted strings together. */
const parse = (line: string) =>
  [...line.matchAll(/"([^"]*)"|'([^']*)'|(\S+)/g)].map(
    (match) => match[1] ?? match[2] ?? match[3] ?? "",
  );

const flag = (args: string[], name: string) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
};

export const HELP: OutputLine[] = [
  {
    kind: "gold",
    text: "# a few aurora verbs work here (the real CLI has 109)",
  },
  {
    kind: "out",
    text: '  aurora boot <id> --task "..."     start a session with ranked lessons',
  },
  {
    kind: "out",
    text: '  aurora learn <id> --experiment NAME --recommend "Use when ..., before ...: ..."',
  },
  { kind: "out", text: "  aurora recall [query]             search lessons" },
  {
    kind: "out",
    text: "  aurora recall-at --path FILE      what to know before you touch FILE",
  },
  {
    kind: "out",
    text: '  aurora recall-at --command "..."  what to know before you run it',
  },
  {
    kind: "out",
    text: "  aurora recall-feedback --source learn:experiment:NAME --useful",
  },
  {
    kind: "out",
    text: "  aurora lock <id> PATH · aurora locks · aurora status · clear",
  },
  {
    kind: "dim",
    text: '# try: aurora recall-at --command "pytest tests/test_server.py"',
  },
];

export const run = (state: PlaygroundState, line: string): OutputLine[] => {
  const words = parse(line.trim());
  if (words.length === 0) return [];
  if (words[0] === "help") return HELP;
  if (words[0] !== "aurora") {
    return [
      {
        kind: "err",
        text: `${words[0]}: not a command here. Type help to see what works.`,
      },
    ];
  }
  const [, verb, ...args] = words;

  switch (verb) {
    case undefined:
    case "help":
    case "--help":
      return HELP;

    case "boot": {
      const id = args[0] && !args[0].startsWith("--") ? args[0] : state.agent;
      const task = flag(args, "--task") ?? "explore";
      const ranked = [...state.lessons]
        .map((lesson) => ({ lesson, score: relevance(lesson, task) }))
        .sort((a, b) => b.score - a.score);
      return [
        {
          kind: "dim",
          text: `# recall-at: armed (${state.lessons.length} lesson(s) warm) -- listening at every edit`,
        },
        { kind: "gold", text: `# CONTEXT for ${id} -- task: ${task}` },
        {
          kind: "out",
          text: `# ${state.lessons.length} lesson(s), 0 blocker(s)`,
        },
        { kind: "out", text: "## LESSONS / CONTEXT (most relevant first)" },
        ...ranked.slice(0, 3).map(({ lesson }) => ({
          kind: "out" as const,
          text: `- ${lesson.recommend}  (source: ${lesson.name})`,
        })),
      ];
    }

    case "learn": {
      const id = args[0] && !args[0].startsWith("--") ? args[0] : state.agent;
      const name = flag(args, "--experiment");
      if (!name)
        return [{ kind: "err", text: "learn needs --experiment NAME" }];
      const recommend =
        flag(args, "--recommend") ??
        flag(args, "--result") ??
        "no advice recorded";
      const success = (flag(args, "--success") ??
        "partial") as Lesson["success"];
      const existing = state.lessons.findIndex(
        (lesson) => lesson.name === name,
      );
      const lesson: Lesson = { name, agent: id, recommend, success, helped: 0 };
      if (existing >= 0) state.lessons.splice(existing, 1, lesson);
      else state.lessons.push(lesson);
      return [
        {
          kind: "ok",
          text: `[OK] recorded lesson '${name}' (category: uncategorized, success: ${success})`,
        },
      ];
    }

    case "recall": {
      const query = args.join(" ");
      const matches = query
        ? state.lessons.filter((lesson) => relevance(lesson, query) >= FLOOR)
        : state.lessons;
      return [
        {
          kind: "gold",
          text: `# ${matches.length} lesson(s) matching '${query}'`,
        },
        ...matches.map((lesson) => ({
          kind: "out" as const,
          text: `  - [uncategorized] ${lesson.name}: ${lesson.recommend} (source: learn:experiment:${lesson.name})`,
        })),
      ];
    }

    case "recall-at": {
      const target = flag(args, "--path") ?? flag(args, "--command");
      if (!target)
        return [
          {
            kind: "err",
            text: 'recall-at needs --path FILE or --command "..."',
          },
        ];
      const shown = state.lessons
        .map((lesson) => ({ lesson, score: relevance(lesson, target) }))
        .filter((item) => item.score >= FLOOR)
        .sort((a, b) => b.score - a.score)
        .slice(0, 3);
      if (shown.length === 0) {
        return [
          {
            kind: "out",
            text: "# recall-at-action: nothing relevant (silence beats a weak hint)",
          },
        ];
      }
      return [
        {
          kind: "gold",
          text: "Recall-at-action (Akashic) - facts relevant to what you're about to do:",
        },
        ...shown.map(({ lesson }) => ({
          kind: "out" as const,
          text: `[${lesson.helped > 0 ? "worked" : "unverified"} ${lesson.agent}${lesson.helped > 0 ? ` helped ${lesson.helped}x` : " advice"}] ${lesson.recommend} (source: learn:experiment:${lesson.name})`,
        })),
      ];
    }

    case "recall-feedback": {
      const source = flag(args, "--source") ?? "";
      const lesson = state.lessons.find(
        (item) =>
          `learn:experiment:${item.name}` === source || item.name === source,
      );
      if (!lesson)
        return [
          {
            kind: "err",
            text: `no lesson at ${source || "(missing --source)"}`,
          },
        ];
      const useful = !args.includes("--noise");
      if (useful) lesson.helped += 1;
      return [
        {
          kind: "ok",
          text: `[recall-feedback] recorded: ${useful ? "useful" : "noise"} <- learn:experiment:${lesson.name}`,
        },
      ];
    }

    case "lock": {
      const id = args[0] ?? state.agent;
      const path = args[1];
      if (!path) return [{ kind: "err", text: "lock needs <id> PATH" }];
      const holder = state.locks.get(path);
      if (holder && holder !== id)
        return [
          { kind: "err", text: `[lock] refused: ${path} is held by ${holder}` },
        ];
      state.locks.set(path, id);
      return [
        {
          kind: "ok",
          text: `[lock] held: ${path}  (you=${id}, token ${state.locks.size})`,
        },
      ];
    }

    case "locks":
      return [
        {
          kind: "gold",
          text: `# ${state.locks.size} advisory path-lock(s) held`,
        },
        ...[...state.locks].map(([path, holder], index) => ({
          kind: "out" as const,
          text: `  ${path}  <- ${holder}  token ${index + 1}  [0s old, ttl 900s]`,
        })),
      ];

    case "status":
      return [
        { kind: "gold", text: "# system status" },
        {
          kind: "out",
          text: "  backend     : files (+ embedded Redis when it is up)",
        },
        { kind: "out", text: `  learnings   : ${state.lessons.length}` },
        { kind: "out", text: `  locks       : ${state.locks.size}` },
      ];

    default:
      return [
        {
          kind: "err",
          text: `aurora ${verb}: not in the playground. The real CLI has ${liveNumbers.cliVerbs} verbs; try help.`,
        },
      ];
  }
};

export const SUGGESTIONS = [
  'aurora recall-at --command "pytest tests/test_server.py"',
  'aurora learn me --experiment css-tokens --recommend "Use when you edit theme colors, before you add one: reuse the tokens in tokens.css."',
  "aurora recall-at --path src/styles/tokens.css",
  "aurora recall-at --path docs/brand/palette.md",
  "aurora recall-feedback --source learn:experiment:css-tokens --useful",
  "aurora status",
];
