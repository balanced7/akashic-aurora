import translations from "~/modules/marketing/content/generated/tool-translations.json";

/**
 * Integration facts. Support levels follow what the docs state, nothing more:
 * quickstart.mdx (setup launchers), how-to/recall-before-you-act.mdx (hooks),
 * concepts/coordination/doors.mdx (MCP), concepts/bifrost/wake.mdx and runners.mdx (seats).
 */

export type Support = "yes" | "manual" | "none";

export interface Integration {
  readonly slug: string;
  readonly name: string;
  readonly tagline: string;
  readonly setup: Support;
  readonly hooks: Support;
  readonly mcp: Support;
  readonly seat: Support;
  readonly launcher?: string;
  readonly hookCommand?: string;
  readonly notes: readonly string[];
  readonly translationKey?: string;
}

export const integrations: readonly Integration[] = [
  {
    slug: "claude-code",
    name: "Claude Code",
    tagline:
      "The primary hook target. Lessons arrive before every edit and shell command.",
    setup: "yes",
    hooks: "yes",
    mcp: "none",
    seat: "yes",
    launcher: "claude",
    hookCommand: "aurora hooks install --scope user",
    notes: [
      "User scope writes ~/.claude/settings.json. Project scope writes the project's .claude/settings.local.json, which git ignores. Add --shared to write the committed .claude/settings.json instead.",
      "The installer writes the full hook set, including PostToolUse, which flip credit needs.",
      "Once on, a hook runs before each edit or shell command in the repo and passes the path or the command.",
      "The edit hook blocks an edit to a path someone else holds.",
      "Boot sees CLAUDE_CODE_SESSION_ID and assumes a session-start hook already gave you a short primer.",
    ],
    translationKey: "Claude Code",
  },
  {
    slug: "codex",
    name: "Codex",
    tagline: "One-paste setup, hooks with a flag, and a seat on the bus.",
    setup: "yes",
    hooks: "yes",
    mcp: "none",
    seat: "yes",
    launcher: "codex",
    hookCommand: "aurora hooks install --scope user --harness codex",
    notes: [
      "Add --harness codex to the hook installer.",
      "Seats on the bus are documented for Claude Code, Cursor and Codex.",
    ],
    translationKey: "Codex",
  },
  {
    slug: "cursor",
    name: "Cursor",
    tagline: "Hooks with a flag, plus Aurora's verbs as native MCP tools.",
    setup: "yes",
    hooks: "yes",
    mcp: "yes",
    seat: "yes",
    launcher: "cursor-agent",
    hookCommand: "aurora hooks install --scope user --harness cursor",
    notes: [
      "Add --harness cursor to the hook installer.",
      "Cursor speaks MCP, so it gets Aurora's verbs as native tools.",
      "An agent in Cursor runs only when it has a turn. Wake gives it a turn when mail lands.",
    ],
    translationKey: "Cursor",
  },
  {
    slug: "gemini-cli",
    name: "Gemini CLI",
    tagline:
      "One-paste setup today. Keep the manual recall habit until hooks land.",
    setup: "yes",
    hooks: "manual",
    mcp: "none",
    seat: "none",
    launcher: "gemini",
    notes: [
      "Paste the setup prompt and Gemini CLI wires Aurora in for you.",
      "In tools without hook wiring, keep the manual habit: run recall-at before you act.",
    ],
    translationKey: "Gemini CLI",
  },
  {
    slug: "opencode",
    name: "OpenCode",
    tagline:
      "One-paste setup today. Keep the manual recall habit until hooks land.",
    setup: "yes",
    hooks: "manual",
    mcp: "none",
    seat: "none",
    launcher: "opencode --prompt",
    notes: [
      "Paste the setup prompt with opencode --prompt and it asks before running anything.",
      "In tools without hook wiring, keep the manual habit: run recall-at before you act.",
    ],
    translationKey: "OpenCode",
  },
];

/** The three doors from the deck, plus the hooks that push recall in without asking. */
export const doors = [
  {
    name: "Shell CLI",
    kind: "CLI",
    body: "aurora <verb> from any directory. 121 verbs on the live checkout and 127 on the merged branch, most with --json.",
    doc: "concepts/coordination/doors",
  },
  {
    name: "MCP tools",
    kind: "MCP",
    body: "boot, recall and learn as native tools for Claude Code, Codex, Cursor and Claude Desktop. 76 tools live, 78 merged.",
    doc: "concepts/coordination/doors",
  },
  {
    name: "Runner ToolBox",
    kind: "Runner",
    body: "knowledge_boot, knowledge_recall and knowledge_learn for API-model seats such as DeepSeek, Kimi, GPT and Gemini. 47 guarded tools.",
    doc: "concepts/bifrost/runners",
  },
  {
    name: "Hooks",
    kind: "Hooks",
    body: "Claude, Codex and Cursor push recall in before an edit or command without anyone asking. Fail-open, always.",
    doc: "concepts/memory/recall-at-action",
  },
] as const;

export const doorsWhy =
  "Three doors exist because a seat that cannot open one cannot use the memory at all. A read-only seat with no shell once could not finish step 1 of the setup guide. A parity checker now fails when the doors drift apart.";

export const getIntegration = (slug: string) =>
  integrations.find((item) => item.slug === slug);

export interface TranslationRow {
  readonly term: string;
  readonly meaning: string;
  readonly same: boolean;
  readonly links: Record<string, string>;
}

export interface TranslationCallout {
  readonly concept: string;
  readonly doc: string;
  readonly differs: string;
  readonly rows: readonly TranslationRow[];
}

export const translationTools: readonly string[] = translations.tools;
export const translationCallouts =
  translations.callouts as readonly TranslationCallout[];
