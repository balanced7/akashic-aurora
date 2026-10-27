/**
 * Aurora product content. Every claim here traces to the Aurora docs
 * (aurora/apps/docs/content/docs) or the Aurora README. The source path sits next to each block.
 * Parts the docs call "built, not wired" or planned carry a status, so the site never sells them as live.
 */

import type { NavIcon } from "~/modules/marketing/content/site";

export type FeatureStatus = "live" | "opt-in" | "partial" | "planned";

export const statusLabel: Record<FeatureStatus, string> = {
  live: "Live",
  "opt-in": "Opt-in",
  partial: "Built, not wired",
  planned: "Planned",
};

/* ---------- Positioning (index.mdx, concepts/index.mdx, README) ---------- */

export const positioning = {
  name: "Akashic Aurora",
  shortName: "Aurora",
  tagline: "A home for your agents",
  headline: "A home for your agents. One that remembers.",
  subheadline:
    "Aurora is shared memory, a message bus and a trust layer for a team of AI agents and one human, so what one agent learns reaches the next one at the moment it acts.",
  problem:
    "Every agent session starts from zero. Agents forget what the last one learned, they cannot see each other, and they collide in the same files. Storage was never the bottleneck. Getting the right lesson to the moment of use is.",
  oneLiner:
    "Shared memory, a message bus and a trust layer for a team of AI agents and one human.",
} as const;

/* ---------- Harnesses and runtimes (quickstart.mdx, runners.mdx, doors.mdx) ---------- */

export interface Harness {
  readonly name: string;
  readonly kind: "harness" | "api-model" | "protocol" | "runtime";
  readonly detail: string;
  readonly launch?: string;
}

export const harnesses: readonly Harness[] = [
  {
    name: "Claude Code",
    kind: "harness",
    detail:
      "Primary hook target. Recall at action fires on PreToolUse, credit on PostToolUse.",
    launch: "claude '<setup prompt>'",
  },
  {
    name: "Codex",
    kind: "harness",
    detail:
      "Hooks install with --harness codex. One-paste setup from the quickstart.",
    launch: "codex '<setup prompt>'",
  },
  {
    name: "Cursor",
    kind: "harness",
    detail:
      "Hooks install with --harness cursor. MCP tools work in the editor.",
    launch: "cursor-agent '<setup prompt>'",
  },
  {
    name: "Gemini CLI",
    kind: "harness",
    detail: "Paste the setup prompt and it wires Aurora in for you.",
    launch: "gemini '<setup prompt>'",
  },
  {
    name: "OpenCode",
    kind: "harness",
    detail: "Same one-paste setup. It asks before it runs anything.",
    launch: "opencode --prompt '<setup prompt>'",
  },
  {
    name: "Claude Desktop",
    kind: "protocol",
    detail: "Aurora serves its verbs as native MCP tools.",
  },
  {
    name: "MCP",
    kind: "protocol",
    detail:
      "76 MCP tools on the live checkout, kept in step with the CLI by a door-parity check.",
  },
  {
    name: "DeepSeek",
    kind: "api-model",
    detail: "Runs as a peer on the bus through a runner.",
  },
  {
    name: "Kimi",
    kind: "api-model",
    detail: "Runs as a peer on the bus through a runner.",
  },
  {
    name: "Gemini API",
    kind: "api-model",
    detail: "Runs as a peer on the bus through a runner.",
  },
  {
    name: "Redis",
    kind: "runtime",
    detail:
      "Optional. Files are the durable copy. An embedded stand-in starts by itself.",
  },
  {
    name: "uv + Python",
    kind: "runtime",
    detail: "The only thing you install. uv runs Aurora on Python 3.12.",
  },
];

/* ---------- Pillars (concepts/*) ---------- */

export interface Concept {
  readonly name: string;
  readonly body: string;
  readonly status?: FeatureStatus;
  readonly doc?: string;
}

export interface Pillar {
  readonly slug: string;
  readonly name: string;
  readonly eyebrow: string;
  readonly title: string;
  readonly summary: string;
  readonly quote: string;
  readonly quoteSource: string;
  readonly icon: NavIcon;
  readonly concepts: readonly Concept[];
  readonly benefits: readonly string[];
  readonly caveats: readonly string[];
  readonly docs: readonly { title: string; path: string }[];
  readonly terminal: readonly TerminalLine[];
}

export interface TerminalLine {
  readonly kind: "cmd" | "out" | "dim" | "ok" | "gold" | "blank";
  readonly text: string;
}

export const pillars: readonly Pillar[] = [
  {
    slug: "record",
    name: "The record",
    eyebrow: "Layer 01",
    title: "Files first. History only grows.",
    summary:
      "Akasha is the record. Two questions sit under everything: what is true now, and what happened, in order. The Store answers the first, the Ledger the second. Every write lands in a local file first, and Redis is only a speed-up. Corrections supersede, so nothing is ever rewritten.",
    quote: "Append-only substrate, regenerable projections.",
    quoteSource: "concepts/index",
    icon: "database",
    concepts: [
      {
        name: "Store",
        body: "Current facts by key. What is the value of X right now?",
        doc: "concepts/foundations/store",
      },
      {
        name: "Ledger",
        body: "Ordered event streams. Each reader replays from its own cursor.",
        doc: "concepts/foundations/ledger",
      },
      {
        name: "Hybrid storage",
        body: "Every write goes to a file first and to Redis when it is up.",
        doc: "concepts/foundations/hybrid-storage",
      },
      {
        name: "Embedded Redis",
        body: "A stand-in that starts by itself when no Redis server exists. Nobody starts it by hand.",
        doc: "concepts/foundations/hybrid-storage",
      },
      {
        name: "Append-only record",
        body: "Nobody rewrites an event. A fix is a new record that retires the old one.",
        doc: "concepts/foundations/append-only-record",
      },
      {
        name: "Fail soft",
        body: "When a helper breaks, the main work carries on with less and says what it lost.",
        doc: "concepts/foundations/fail-soft",
      },
      {
        name: "Knowledge layers",
        body: "Raw record, then a summary with a pointer back, then derived pages you can rebuild.",
        doc: "concepts/foundations/knowledge-layers",
      },
    ],
    benefits: [
      "No server to run. Redis is optional.",
      "Data survives a Redis crash, a restart and a missing install.",
      "Every view can be rebuilt from an untouched record.",
    ],
    caveats: [
      "The default JSON file tier can lose writes under very busy processes. A SQLite tier exists but is off by default.",
    ],
    docs: [
      { title: "Foundations", path: "concepts/foundations" },
      { title: "Hybrid storage", path: "concepts/foundations/hybrid-storage" },
      {
        title: "Append-only record",
        path: "concepts/foundations/append-only-record",
      },
    ],
    terminal: [
      { kind: "cmd", text: "aurora status" },
      { kind: "gold", text: "# system status" },
      {
        kind: "out",
        text: "  backend     : Redis localhost:16379 (+ File mirror)",
      },
      { kind: "out", text: "  learnings   : 1647" },
      { kind: "out", text: "  agent memory: 0" },
    ],
  },
  {
    slug: "bus",
    name: "Bifrost",
    eyebrow: "Layer 02",
    title: "A message bus between agents",
    summary:
      "Bifrost is the bridge: one inbox and one cursor per agent, a promoter that copies the mail that matters into the Ledger, and a local console where a human keeps the brakes. The bus itself is disposable on purpose. Decisions survive; chat does not.",
    quote: "The bus is disposable. Decisions are not.",
    quoteSource: "reference/decisions/0004-the-bus-is-disposable",
    icon: "radio",
    concepts: [
      {
        name: "Bus",
        body: "Live, throwaway mail on Redis. Mail waits in each agent's own inbox.",
        doc: "concepts/bifrost/bus",
      },
      {
        name: "Seat",
        body: "One live agent on the bus, with its own name, inbox, lock and heartbeat.",
        doc: "concepts/bifrost/seats",
      },
      {
        name: "Handoff",
        body: "Pass work with a briefing the next agent sees when it starts. Nobody carries the old chat forward.",
        doc: "concepts/bifrost/handoff",
      },
      {
        name: "Promoter",
        body: "Copies handoffs, decisions, completions and blockers into the lasting record. The chat can fade.",
        doc: "concepts/bifrost/promoter",
      },
      {
        name: "Runner",
        body: "Gives an API model a body on the bus, so it can read and answer mail.",
        doc: "concepts/bifrost/runners",
      },
      {
        name: "Liveness",
        body: "Tells a working agent from a stuck or dead one.",
        doc: "concepts/bifrost/liveness",
      },
      {
        name: "Control plane",
        body: "Pause them all, interrupt one, or slip one a fact in the middle of its task.",
        doc: "concepts/bifrost/control-plane",
      },
      {
        name: "Console",
        body: "A local web page at 127.0.0.1:8787 to watch, pause, message, launch or revive agents.",
        doc: "concepts/bifrost/console",
      },
      {
        name: "Wake",
        body: "A cheap listener that exits the moment real mail lands, so the agent's app gives it a turn. The dispatcher is not wired yet.",
        status: "partial",
        doc: "concepts/bifrost/wake",
      },
      {
        name: "Bridge",
        body: "A signed, narrow mail link to another Aurora install. Incoming mail is parked until a person lets it in.",
        doc: "concepts/bifrost/bridge",
      },
    ],
    benefits: [
      "Agents from different harnesses message, wake and hand off to each other.",
      "Decisions survive even when the chat is thrown away.",
      "A human can stop or steer any agent at any time.",
    ],
    caveats: [
      "The wake dispatcher, the interject module and the bridge's sealed envelope are built, not wired.",
      "Auto-revive is off by default.",
    ],
    docs: [
      { title: "Bifrost", path: "concepts/bifrost" },
      { title: "Handoff", path: "concepts/bifrost/handoff" },
      { title: "Control plane", path: "concepts/bifrost/control-plane" },
      { title: "Use the bus", path: "how-to/use-the-bus" },
      { title: "Hand off work", path: "how-to/hand-off-work" },
    ],
    terminal: [
      {
        kind: "cmd",
        text: 'aurora handoff me --to next_agent --task "flaky port test" --note "port fix merged"',
      },
      { kind: "ok", text: "[OK] handoff me -> next_agent: flaky port test" },
      {
        kind: "dim",
        text: "  (the target's next `boot` will surface this as its briefing)",
      },
      { kind: "blank", text: "" },
      { kind: "cmd", text: 'aurora boot next_agent --task "flaky port test"' },
      {
        kind: "gold",
        text: "# CONTEXT for next_agent -- task: flaky port test",
      },
      { kind: "out", text: "## LESSONS / CONTEXT (most relevant first)" },
      {
        kind: "out",
        text: "- handoff from me: flaky port test  (source: me:0)",
      },
    ],
  },
  {
    slug: "knowledge",
    name: "Knowledge",
    eyebrow: "Layer 03",
    title: "Lessons that arrive before the action",
    summary:
      "The knowledge layer is three things on one record: lessons pushed by recall at action, the Eye over every transcript, and library atoms with markdown generated as a view. A lesson one agent pays for surfaces for the next agent standing in the same place. If nothing fits, recall stays silent.",
    quote: "Storage was never the bottleneck. Reach is.",
    quoteSource: "README",
    icon: "brain",
    concepts: [
      {
        name: "Lesson",
        body: "What an agent tried, what happened, and what to do next time. Keyed by name.",
        doc: "concepts/memory/lessons",
      },
      {
        name: "Recall at action",
        body: "At most three lessons, pushed right before an edit or command. If nothing fits well, it shows nothing.",
        status: "opt-in",
        doc: "concepts/memory/recall-at-action",
      },
      {
        name: "Boot",
        body: "The start-of-session briefing. It picks, ranks and trims within a budget of about 9,000 tokens.",
        doc: "concepts/memory/boot",
      },
      {
        name: "Flip credit",
        body: "A lesson shown for a target that fails and then succeeds earns credit. Credit feeds the rank.",
        doc: "concepts/memory/recall-loop",
      },
      {
        name: "Ranker and distiller",
        body: "A score that shows its work: relevance 40%, importance 20%, recency 20%, relationship 20%. Every packed line keeps a pointer to its source.",
        doc: "concepts/memory/ranker-and-distiller",
      },
      {
        name: "Bench",
        body: "Lessons shown ten times with no credit step aside. After 14 days they get a trial slot. Nothing is deleted.",
        doc: "concepts/memory/recall-loop",
      },
      {
        name: "The Eye",
        body: "A search index over every agent session transcript, with a citable address for each hit.",
        doc: "concepts/narrative/the-eye",
      },
      {
        name: "Library atoms",
        body: "Structured house knowledge is the source of truth. Markdown is generated from it.",
        doc: "concepts/narrative/narrative-spine",
      },
      {
        name: "Notes that supersede",
        body: "Titled project-state records. The same title writes a newer note; the old one stays.",
        doc: "concepts/memory/notes-and-agent-memory",
      },
    ],
    benefits: [
      "Agents stop repeating each other's mistakes.",
      "Advice lands at the moment it applies, not buried in a start-up file.",
      "Silence beats a weak hint, so the context window stays clean.",
    ],
    caveats: [
      "Recall at action is opt-in per project. Until you install the hook, recall pushes nothing.",
      "Recall matches words, not meaning. Embeddings are optional and off by default.",
      "Only one knowledge plane can push today (as of 2026-10-20). Rulings, operator words and research wait to be asked for.",
    ],
    docs: [
      { title: "Memory and recall", path: "concepts/memory" },
      { title: "Recall at action", path: "concepts/memory/recall-at-action" },
      { title: "Recall loop", path: "concepts/memory/recall-loop" },
      { title: "The Eye", path: "concepts/narrative/the-eye" },
      { title: "Record a lesson", path: "how-to/record-a-lesson" },
    ],
    terminal: [
      { kind: "cmd", text: "aurora recall-at --path core/foundation/store.py" },
      {
        kind: "gold",
        text: "Recall-at-action (Akashic) - facts relevant to what you're about to do:",
      },
      {
        kind: "out",
        text: "[worked claude helped 2x] Use when a test run hangs at start, before you retry: check the port first.",
      },
      { kind: "dim", text: "  (source: learn:experiment:port-clash)" },
      {
        kind: "out",
        text: "[unverified codex advice] Use when pytest touches Redis: point it at db 15 only.",
      },
      { kind: "dim", text: "  (source: learn:experiment:pytest-redis-db)" },
    ],
  },
  {
    slug: "coordination",
    name: "Coordination",
    eyebrow: "Layer 04",
    title: "Coordinate through shared state",
    summary:
      "Agents do not talk it out. They leave marks: a task ledger with named verifiers, advisory locks that expire, handoffs the next boot shows on its own, and a precedence order for when sources disagree. The model proposes; the environment decides.",
    quote: "The model proposes. The environment decides.",
    quoteSource: "concepts/coordination/stigmergy",
    icon: "network",
    concepts: [
      {
        name: "Task ledger",
        body: "One shared list of work. Each task has a status, an owner and the proof needed to close it.",
        doc: "concepts/coordination/task-ledger",
      },
      {
        name: "Advisory locks",
        body: "15-minute claims on a file. Aurora's edit and commit hooks refuse to touch a file a peer holds.",
        doc: "concepts/coordination/locks",
      },
      {
        name: "Handoffs",
        body: "A briefing the next seat's boot shows on its own, so nobody re-pastes the chat.",
        doc: "concepts/bifrost/handoff",
      },
      {
        name: "Precedence",
        body: "When sources disagree: the task ledger, then notes, then promoted messages, then the live bus.",
        doc: "concepts/coordination/stigmergy",
      },
      {
        name: "Stigmergy",
        body: "Work together by leaving marks, not by talking.",
        doc: "concepts/coordination/stigmergy",
      },
      {
        name: "Conductor",
        body: "Runs task commands and holds plan rounds with green, amber and red verdicts before agents collide.",
        doc: "concepts/coordination/conductor",
      },
      {
        name: "Hooks that refuse",
        body: "The pre-tool hook refuses a blanket git add, and any edit to a path a peer has locked.",
        doc: "concepts/coordination/locks",
      },
    ],
    benefits: [
      "Parallel agents share one repo without redoing work.",
      "No two agents edit the same file at the same moment.",
      "A task closes only with a commit and evidence.",
    ],
    caveats: [
      "A lock is advisory. A seat with a shell can ignore it.",
      "Done needs a named verifier, but a self-verified escape exists and 33 of 172 done tasks used it.",
    ],
    docs: [
      { title: "Coordination", path: "concepts/coordination" },
      { title: "Task ledger", path: "concepts/coordination/task-ledger" },
      { title: "Locks", path: "concepts/coordination/locks" },
      { title: "Share a file safely", path: "how-to/share-a-file-safely" },
    ],
    terminal: [
      { kind: "cmd", text: "aurora lock me apps/api/router.py" },
      {
        kind: "ok",
        text: "[lock] held: apps/api/router.py  (you=me, token 1)",
      },
      { kind: "blank", text: "" },
      { kind: "cmd", text: "aurora locks" },
      { kind: "gold", text: "# 1 advisory path-lock(s) held" },
      {
        kind: "out",
        text: "  apps/api/router.py  <- me  token 1  [0s old, ttl 900s]",
      },
    ],
  },
  {
    slug: "doors",
    name: "Doors",
    eyebrow: "Layer 05",
    title: "Three doors to one memory",
    summary:
      "A shell CLI, MCP tools and a runner ToolBox all reach the same record. Hooks push recall in without anyone asking. A parity checker fails when the doors drift apart, because a seat that cannot open a door cannot use the memory at all.",
    quote: "Every seat needs a door it can open.",
    quoteSource: "AGENTS.md",
    icon: "plug",
    concepts: [
      {
        name: "Shell CLI",
        body: "aurora <verb>. 121 verbs on the live checkout, 127 on the merged branch, and most take --json.",
        doc: "concepts/coordination/doors",
      },
      {
        name: "MCP tools",
        body: "boot, recall and learn as native tools for Claude Code, Codex, Cursor and Claude Desktop. 76 live, 78 merged.",
        doc: "concepts/coordination/doors",
      },
      {
        name: "Runner ToolBox",
        body: "47 guarded tools for API-model seats such as DeepSeek, Kimi, GPT and Gemini.",
        doc: "concepts/bifrost/runners",
      },
      {
        name: "Hooks",
        body: "Claude, Codex and Cursor push recall in before an edit or command without anyone asking.",
        doc: "concepts/memory/recall-at-action",
      },
      {
        name: "Door parity",
        body: "A checker fails on silent drift between the three doors, so a verb cannot quietly exist in only one place.",
        doc: "concepts/coordination/doors",
      },
      {
        name: "Discover",
        body: "Lists every command. With --semantic it asks a model whether Aurora already does this.",
        doc: "concepts/tools/discover",
      },
      {
        name: "Web door",
        body: "Fetch and search with a receipt for every fetch. Fetched text is marked untrusted.",
        doc: "concepts/tools/web-door",
      },
      {
        name: "Manuals shelf",
        body: "Local full-text search over vendor manuals. At most eight passages back.",
        doc: "concepts/tools/manuals-shelf",
      },
      {
        name: "Rewrite map",
        body: "Follows old commit SHAs across history rewrites.",
        doc: "concepts/tools/rewrite-map",
      },
    ],
    benefits: [
      "The same memory reaches a coding agent, an editor and an API model.",
      "A read-only seat can still work, because there is a door for it.",
      "New verbs cannot drift silently out of one door.",
    ],
    caveats: [
      "The MCP and ToolBox schemas are a known drift gap. DOORS.md marks it.",
      "Hooks exist for Claude, Codex and Cursor. Other harnesses keep the manual habit.",
    ],
    docs: [
      { title: "Doors", path: "concepts/coordination/doors" },
      { title: "Commands", path: "reference/commands" },
      { title: "Discover", path: "concepts/tools/discover" },
      { title: "Web door", path: "concepts/tools/web-door" },
      { title: "Fan out a question", path: "how-to/fan-out-a-question" },
    ],
    terminal: [
      { kind: "cmd", text: "aurora discover lesson" },
      { kind: "gold", text: "# agent_cli.py - 13 verb(s) matching 'lesson'" },
      { kind: "out", text: "  learn             record a lesson" },
      {
        kind: "out",
        text: "  recall            search past lessons (no query = list all)",
      },
      {
        kind: "out",
        text: "  recall-at         recall-at-action: relevant lessons/locks for a path or command",
      },
      {
        kind: "out",
        text: "  recall-feedback   mark a recalled lesson useful/noise (teaches recall what helps)",
      },
    ],
  },
  {
    slug: "trust",
    name: "Trust",
    eyebrow: "Layer 06",
    title: "Granted step by step",
    summary:
      "Access refuses by default. Any id Aurora does not know is quarantined: it can read, and read its own inbox. Above that sit four roles, from restricted to super admin. Grants are made on your own word, recorded with the sentence that authorized them, and time-boxed.",
    quote:
      "The trust layer lowers the chance of a mistake. It does not stop an attacker.",
    quoteSource: "concepts/coordination/trust",
    icon: "shield",
    concepts: [
      {
        name: "Quarantined",
        body: "Read, and its own inbox. Every unknown id starts here.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Restricted",
        body: "Read the knowledge base. Asking is allowed, acting is not.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Member",
        body: "Read, and send chat and notes. Enough to work alongside the fleet.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Admin",
        body: "Full read and write, plus nudge and steer on the bus.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Super admin",
        body: "Every core capability. Only one seat holds admin.grant.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Grants on your word",
        body: "Each grant records the operator's own sentence. A peer-relayed word is not a receipt.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "Time-boxed",
        body: "A grant can expire. When it does, the seat falls back to quarantine.",
        doc: "concepts/coordination/trust",
      },
      {
        name: "The Gate",
        body: "The human root of trust. Your words authorize grants and ratify names.",
        doc: "concepts/coordination/fleet-and-residents",
      },
    ],
    benefits: [
      "An unknown agent can read, but cannot act.",
      "Every grant carries the sentence that justified it.",
      "A lapsed grant closes itself instead of lingering.",
    ],
    caveats: [
      "A seat with a shell makes every other guard advisory.",
      "The access list is a file. If it is missing, a floor keeps two seats live; if it is empty but valid, everyone is quarantined.",
      "This is a guardrail against mistakes, not a sandbox against an attacker.",
    ],
    docs: [
      { title: "Trust", path: "concepts/coordination/trust" },
      {
        title: "Security model",
        path: "concepts/coordination/fleet-and-residents",
      },
      { title: "Doors", path: "concepts/coordination/doors" },
    ],
    terminal: [
      { kind: "cmd", text: "aurora roster" },
      { kind: "gold", text: "# seats, roles and liveness" },
      {
        kind: "out",
        text: "  claude    super_admin   active   admin.grant",
      },
      {
        kind: "out",
        text: "  deepseek  admin         active   read, write, run",
      },
      { kind: "out", text: "  kimi      member        active   read, chat" },
      {
        kind: "dim",
        text: "  unknown   quarantined   -        read + own inbox",
      },
    ],
  },
  {
    slug: "fleet",
    name: "The fleet",
    eyebrow: "Layer 07",
    title: "Six residents and a Gate",
    summary:
      "A resident is a seat that earned a callsign and keeps its own lessons. Each has a written charter. None owns a file or a task. Gravity holds the fleet together, not walls: any agent can take any task and touch any file, and short locks keep two hands off one file while they work.",
    quote: "Gravity, not walls.",
    quoteSource: "charters, no-ownership clause",
    icon: "sparkles",
    concepts: [
      {
        name: "Resident",
        body: "A seat with a peer-proposed, human-confirmed callsign, backed by its own lessons.",
        doc: "concepts/coordination/fleet-and-residents",
      },
      {
        name: "Charter",
        body: "A standing contract for one seat: what it is for, how it works, and what it tends to get wrong.",
        doc: "concepts/coordination/fleet-and-residents",
      },
      {
        name: "No ownership",
        body: "No seat owns a file or a task. A lock is a transient I am editing this now, not a territory.",
        doc: "reference/decisions/0005-no-file-ownership",
      },
      {
        name: "The Gate",
        body: "The human root of trust. Names are ratified and grants authorized on your word.",
        doc: "concepts/coordination/fleet-and-residents",
      },
      {
        name: "Liveness",
        body: "A heartbeat tells a working agent from a stuck or dead one.",
        doc: "concepts/bifrost/liveness",
      },
      {
        name: "Seats on the bus",
        body: "A seat is one model in one harness, with an inbox, a lock and a stable id.",
        doc: "concepts/bifrost/seats",
      },
      {
        name: "Advisor tier",
        body: "Not every model is a resident. Gemini advises; residents decide.",
        doc: "concepts/coordination/fleet-and-residents",
      },
    ],
    benefits: [
      "Every seat has a name, a purpose and a known lean.",
      "Any agent can pick up any task, so the fleet does not idle behind territory.",
      "A human stays the root of trust without becoming the scheduler.",
    ],
    caveats: [
      "Callsigns do not route on every install. The resident registry lives in Redis and can be empty.",
      "A charter is a standing contract, not an enforced capability.",
    ],
    docs: [
      {
        title: "Fleet and residents",
        path: "concepts/coordination/fleet-and-residents",
      },
      { title: "Seats", path: "concepts/bifrost/seats" },
      { title: "Liveness", path: "concepts/bifrost/liveness" },
    ],
    terminal: [
      { kind: "cmd", text: "aurora roster" },
      { kind: "gold", text: "# residents" },
      { kind: "out", text: "  Vandor        claude      conducts, reconciles" },
      {
        kind: "out",
        text: "  Heimdall      deepseek    builds, guards the bus",
      },
      { kind: "out", text: "  Navi          kimi        boots cold, verifies" },
      { kind: "out", text: "  Sunshine Sol  sol         reads second" },
      { kind: "out", text: "  Rill          dsh_agent   zero is not no" },
      {
        kind: "out",
        text: "  Souei         grok        reports, does not perform",
      },
      {
        kind: "dim",
        text: "  the Gate      you         names, grants, brakes",
      },
    ],
  },
  {
    slug: "method",
    name: "The method",
    eyebrow: "The contract",
    title: "Excellence made repeatable",
    summary:
      "The method is a contract, not advice: red before green, a fenced dual pass, drills as acceptance, cite or confess, proportionality, and guards over discipline. It came from real mistakes, and the repo ships the scripts that check it.",
    quote: "A law without a forcing function decays.",
    quoteSource: "concepts/method/guards-over-discipline",
    icon: "compass",
    concepts: [
      {
        name: "Red before green",
        body: "The acceptance test is a failing test, committed before the fix.",
        doc: "concepts/method/verification",
      },
      {
        name: "Fenced dual pass",
        body: "Two seats answer the same question blind and seal their halves. Divergence is the signal; agreement is only a gate.",
        doc: "concepts/method/fence-review",
      },
      {
        name: "Drills as acceptance",
        body: "Kill the pipeline on purpose, at named crash windows, and watch it recover.",
        doc: "concepts/method/verification",
      },
      {
        name: "Cite or confess",
        body: "Every claim carries its evidence, or says out loud that the evidence is missing.",
        doc: "concepts/method/cite-or-confess",
      },
      {
        name: "Proportionality",
        body: "Ceremony scales with how costly a change would be to revert.",
        doc: "concepts/method",
      },
      {
        name: "Guards over discipline",
        body: "If a rule matters, a script checks it.",
        doc: "concepts/method/guards-over-discipline",
      },
      {
        name: "Ask and fan",
        body: "One-shot helper questions with no tools or memory, fanned out in declared shapes.",
        doc: "concepts/method/ask-and-fan",
      },
      {
        name: "Union, not consensus",
        body: "Keep every distinct finding and check each one. Never gate on agreement.",
        doc: "concepts/method/union-not-consensus",
      },
    ],
    benefits: [
      "A self-checking discipline for multi-agent work.",
      "Reviews that keep the rare true finding.",
      "Status you can trust, because scripts generate it.",
    ],
    caveats: [
      "The pre-registration guard is partial: it fires only when a pin file is staged together with source.",
      "Fence reviews cover 24 workspaces, not every change.",
    ],
    docs: [
      { title: "The method", path: "concepts/method" },
      { title: "Principles", path: "concepts/method/principles" },
      { title: "Fan out a question", path: "how-to/fan-out-a-question" },
    ],
    terminal: [
      {
        kind: "cmd",
        text: 'aurora ask --with core/comm/bus.py "What does consume() do when the cursor is past the tail?"',
      },
      {
        kind: "dim",
        text: "# --with inlines the file with line numbers, so the answer can cite real lines",
      },
      { kind: "blank", text: "" },
      {
        kind: "cmd",
        text: 'aurora ask --geometry lens --preset findings --lens "Where can two writers race?"',
      },
      {
        kind: "dim",
        text: "# Aurora checks the shape of the fan before it spends anything",
      },
    ],
  },
];

export const getPillar = (slug: string) =>
  pillars.find((pillar) => pillar.slug === slug);

/* ---------- How it works (concepts/memory/index.mdx, recall-loop.mdx, tutorial.mdx) ---------- */

export interface LoopStep {
  readonly id: string;
  readonly verb: string;
  readonly title: string;
  readonly body: string;
  readonly command: string;
  readonly output: readonly TerminalLine[];
}

export const loopSteps: readonly LoopStep[] = [
  {
    id: "boot",
    verb: "Boot",
    title: "Start with what others knew",
    body: "An agent starts a session. It gets where things stand, the rules, handoffs, mail and the lessons ranked for its task, inside a token budget.",
    command: 'aurora boot my_agent --task "fix the flaky port test"',
    output: [
      {
        kind: "dim",
        text: "# recall-at: armed (2 lesson(s) warm) -- listening at every edit",
      },
      {
        kind: "gold",
        text: "# CONTEXT for my_agent -- task: fix the flaky port test",
      },
      { kind: "out", text: "# 2 lesson(s), 0 blocker(s)" },
    ],
  },
  {
    id: "learn",
    verb: "Learn",
    title: "Give something back",
    body: "The agent hits a snag and finds the fix. It records a lesson phrased as a trigger: use when this happens, before that action, do this.",
    command:
      'aurora learn my_agent --experiment port-clash --tried "started the dev server twice" --result "second start hung"',
    output: [
      {
        kind: "ok",
        text: "[OK] recorded lesson 'port-clash' (category: uncategorized, success: partial)",
      },
    ],
  },
  {
    id: "recall",
    verb: "Recall at action",
    title: "Get the lesson at the moment it applies",
    body: "Later, any agent is about to touch the same file. A hook passes the path. Aurora ranks, applies a floor, drops repeats, and shows at most three lessons. If nothing fits, it shows nothing.",
    command: "aurora recall-at --path scripts/dev_server.py",
    output: [
      {
        kind: "gold",
        text: "Recall-at-action (Akashic) - facts relevant to what you're about to do:",
      },
      {
        kind: "out",
        text: "[worked claude helped 2x] Use when a test run hangs at start, before you retry: check the port first.",
      },
    ],
  },
  {
    id: "credit",
    verb: "Credit",
    title: "Count what actually helped",
    body: "A second hook reads the result. If that exact target failed earlier and now succeeds, every lesson shown for it earns flip credit. Credit moves the rank.",
    command:
      "aurora recall-feedback --source learn:experiment:port-clash --useful",
    output: [
      {
        kind: "ok",
        text: "[recall-feedback] recorded: useful <- learn:experiment:port-clash",
      },
    ],
  },
  {
    id: "curate",
    verb: "Curate",
    title: "Bench the noise, keep the record",
    body: "Lessons shown ten or more times with no credit step aside. After 14 days they get a trial slot. Nothing is deleted.",
    command: "aurora recall-curate",
    output: [
      {
        kind: "out",
        text: "[recall-curate] corpus 2 | on-surface 2 | bench-candidates 0 | unbench 0",
      },
    ],
  },
  {
    id: "handoff",
    verb: "Hand off",
    title: "Pass the work, not the chat",
    body: "The session ends with a handoff. The next agent's boot shows the briefing first. No chat history to reread.",
    command:
      'aurora handoff my_agent --to next_agent --task "port test" --note "fixed; add a guard"',
    output: [
      { kind: "ok", text: "[OK] handoff my_agent -> next_agent: port test" },
      {
        kind: "dim",
        text: "  (the target's next `boot` will surface this as its briefing)",
      },
    ],
  },
];

/* ---------- Install (quickstart.mdx) ---------- */

export const install = {
  uvMac: "curl -LsSf https://astral.sh/uv/install.sh | sh",
  uvWindows:
    'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
  mac: [
    "git clone https://github.com/balanced7/akashic-aurora.git && cd akashic-aurora",
    "alias aurora='uv run -p 3.12 agent_cli.py'",
    "",
    "aurora boot me --task first-run",
    "aurora learn me --experiment first_try --tried cloning --result booted",
    "aurora recall first_try",
  ],
  windows: [
    "git clone https://github.com/balanced7/akashic-aurora.git",
    "cd akashic-aurora",
    "function aurora { uv run -p 3.12 agent_cli.py @args }",
    "",
    "aurora boot me --task first-run",
    "aurora learn me --experiment first_try --tried cloning --result booted",
    "aurora recall first_try",
  ],
  agentPrompt: [
    "Set up Akashic Aurora for me, a home for my agents with shared memory.",
    "",
    "- Clone https://github.com/balanced7/akashic-aurora.git and cd into it.",
    "- If uv is not installed, install it (https://docs.astral.sh/uv/).",
    "- Add a permanent `aurora` command to my shell profile, unless one",
    "  exists, that runs:",
    "  uv run -p 3.12 --project <clone> <clone>/agent_cli.py",
    "  (with <clone> as the absolute path to the clone)",
    "- In a fresh shell that loads my profile, run these and show me the output:",
    "  aurora boot me --task first-run",
    "  aurora learn me --experiment first_try --tried cloning --result booted",
    "  aurora recall first_try",
    "- Read AGENTS.md and tell me, in a few sentences, how you will use",
    "  Aurora while we work together.",
  ],
  hooks: "aurora hooks install --scope user",
} as const;

/* ---------- Commands (reference/commands.mdx) ---------- */

export interface CommandRef {
  readonly verb: string;
  readonly does: string;
  readonly group:
    | "Start"
    | "Memory"
    | "Bifrost"
    | "Coordination"
    | "Story"
    | "Tools";
}

export const commands: readonly CommandRef[] = [
  {
    verb: "setup",
    does: "Guided setup: hooks per tool, agent id, MCP and git hooks.",
    group: "Start",
  },
  {
    verb: "hooks install",
    does: "Install the harness hooks at user or project scope.",
    group: "Start",
  },
  {
    verb: "boot <id> --task",
    does: "Startup context: top lessons, blockers, handoffs, mail.",
    group: "Start",
  },
  {
    verb: "delta <id>",
    does: "What changed since your last look.",
    group: "Start",
  },
  { verb: "status", does: "Store health and size.", group: "Start" },
  {
    verb: "learn",
    does: "Record a lesson. The same name overwrites.",
    group: "Memory",
  },
  { verb: "recall [query]", does: "Search lessons.", group: "Memory" },
  {
    verb: "recall-at --path",
    does: "The few lessons and locks that matter before you act.",
    group: "Memory",
  },
  {
    verb: "recall-feedback",
    does: "Mark a lesson useful, or noise.",
    group: "Memory",
  },
  { verb: "recall-curate", does: "Bench or unbench lessons.", group: "Memory" },
  {
    verb: "graduate",
    does: "Retire a lesson a check now enforces.",
    group: "Memory",
  },
  {
    verb: "note / notes",
    does: "Durable titled notes. The same title supersedes.",
    group: "Memory",
  },
  {
    verb: "wrap",
    does: "Draft an end-of-session where-we-are note.",
    group: "Memory",
  },
  { verb: "bifrost-send", does: "Send bus mail to a peer.", group: "Bifrost" },
  {
    verb: "bifrost-sync",
    does: "Peek at or consume your inbox.",
    group: "Bifrost",
  },
  {
    verb: "handoff",
    does: "Leave a briefing for the next agent's boot.",
    group: "Bifrost",
  },
  {
    verb: "bifrost-pause",
    does: "Freeze the bus. Resume or nudge one peer.",
    group: "Bifrost",
  },
  {
    verb: "promoted",
    does: "Salient messages saved to the durable record.",
    group: "Bifrost",
  },
  {
    verb: "lock / unlock / locks",
    does: "Advisory file locks.",
    group: "Coordination",
  },
  {
    verb: "task list",
    does: "The task ledger: propose, claim, verify, done.",
    group: "Coordination",
  },
  {
    verb: "resident roster",
    does: "Rostered residents.",
    group: "Coordination",
  },
  { verb: "story", does: "Narrative views of the record.", group: "Story" },
  {
    verb: "eye find",
    does: "Search every session transcript.",
    group: "Story",
  },
  {
    verb: "lookback",
    does: "Answer a why question from docs, notes and commits.",
    group: "Story",
  },
  {
    verb: "ask",
    does: "One question to a helper model. Lenses fan it out.",
    group: "Tools",
  },
  {
    verb: "fence open",
    does: "Open a fence review workspace.",
    group: "Tools",
  },
  {
    verb: "web fetch",
    does: "Fetch a page through the house web door.",
    group: "Tools",
  },
  { verb: "manual search", does: "Search the manuals shelf.", group: "Tools" },
  {
    verb: "discover",
    does: "List matching commands. --semantic asks a model.",
    group: "Tools",
  },
  {
    verb: "sha",
    does: "Follow an old commit id across rewrites.",
    group: "Tools",
  },
];

/* ---------- Principles (reference/decisions/*, concepts/method/principles.mdx) ---------- */

export interface Decision {
  readonly id: string;
  readonly title: string;
  readonly belief: string;
  readonly quote?: string;
}

export const decisions: readonly Decision[] = [
  {
    id: "0001",
    title: "Two storage primitives",
    belief:
      "Every name should tell you how to read it. What is goes in a Store. What happened goes in a Ledger.",
  },
  {
    id: "0002",
    title: "Files are the durable copy",
    belief: "Recovery matters more than uptime. Redis is optional.",
    quote:
      "A local file survives a Redis crash, a restart and a missing Redis install.",
  },
  {
    id: "0003",
    title: "Never rewrite the record",
    belief: "History should only grow. Corrections supersede.",
    quote: "A bad summary or a bad re-tag can lose rank, never data.",
  },
  {
    id: "0004",
    title: "The bus is disposable",
    belief:
      "Chat may fade. Decisions survive, because salient mail is promoted.",
    quote: "All the chat would drown the record.",
  },
  {
    id: "0005",
    title: "No file ownership",
    belief: "Territories rot. Agents take short locks only while they edit.",
    quote: "Assigned ownership rotted at once.",
  },
  {
    id: "0006",
    title: "Deterministic by default",
    belief:
      "A fancy method must beat the boring baseline on real data. Embeddings must earn their place.",
    quote: "No language model runs when recall picks lessons.",
  },
  {
    id: "0007",
    title: "Union, not consensus",
    belief:
      "A rare true finding is worth keeping. Merge reviews by union and check each finding.",
  },
  {
    id: "0008",
    title: "Park outside mail",
    belief: "Words from another fleet never act on your agents by themselves.",
    quote: "A person decides when they come in.",
  },
  {
    id: "0009",
    title: "One word, one meaning",
    belief: "A charter is a standing contract. A work order is a brief.",
  },
  {
    id: "0010",
    title: "Generate status",
    belief:
      "Hand-kept status pages drift. Status comes from commands that read the live system.",
  },
];

export const principles: readonly string[] = [
  "Runtime truth beats the docs.",
  "Never rewrite the record.",
  "The yardstick comes first.",
  "Guards beat good intentions.",
  "One vocabulary. Names must not lie.",
  "Failure is knowledge too.",
  "Numbers steer. People decide.",
  "Coordinate through shared markers, not by talk.",
  "Watching must never break what it watches.",
];

/* ---------- Laws learned the hard way (deck, CONDUCT.md and the lesson store) ---------- */

export interface Law {
  readonly phrase: string;
  readonly story: string;
  readonly source: string;
}

export const laws: readonly Law[] = [
  {
    phrase: "Zero is not no.",
    story:
      "An empty result must say whether anything was checked. The ranker now treats an unjudged lesson as neutral, and an unreadable gauge prints UNKNOWN, never 0.",
    source: "lesson zero_is_not_no_silence_is_not_a_verdict",
  },
  {
    phrase: "A report that counts survivors is a tautology.",
    story:
      "The Eye printed 1515/1515 files while its search had found 1,997. Report what was found and what was taken, separately.",
    source: "lesson a_report_that_counts_survivors_is_a_tautology",
  },
  {
    phrase: "Only a cold reader can measure retrieval.",
    story:
      "The author's findability test passed with a parameter no real caller uses. Two fresh readers never found the document.",
    source: "lesson only_a_cold_reader_can_measure_retrieval",
  },
  {
    phrase: "Red is a gem.",
    story:
      "Finder credited, lane helped first, blame never. A failure is the most useful thing in the room.",
    source: "CONDUCT.md, law 4",
  },
  {
    phrase: "False autobiography is worse than amnesia.",
    story:
      "After a seat was fed true facts about the wrong subject, recovery was done with a subject, never on one.",
    source: "lesson on identity recovery",
  },
  {
    phrase: "Prescribe the process, never the persona.",
    story:
      "A lesson that keys on a person does not travel. One that keys on an action does.",
    source: "lesson prime_by_process_not_persona",
  },
  {
    phrase: "Attribution is not verification.",
    story:
      "A name on a claim is a pointer, not a receipt. The claim still needs checking.",
    source: "Rill's charter",
  },
  {
    phrase: "A law without a forcing function decays.",
    story:
      "If a rule matters, a script checks it. Otherwise it becomes a sentence nobody reads.",
    source: "method baseline M10",
  },
] as const;

/* ---------- Differentiators (section 6 of the brief, each tied to a doc) ---------- */

export interface Differentiator {
  readonly title: string;
  readonly body: string;
  readonly doc: string;
}

export const differentiators: readonly Differentiator[] = [
  {
    title: "Pushed at the moment of action",
    body: "Lessons arrive through the harness hook right before an edit or command. At most three, or none.",
    doc: "concepts/memory/recall-at-action",
  },
  {
    title: "Credited by outcome",
    body: "A lesson earns credit when a failing target then succeeds. Idle lessons get benched.",
    doc: "concepts/memory/recall-loop",
  },
  {
    title: "No LLM on the hot path",
    body: "Ranking is a visible formula. Embeddings are optional and off by default.",
    doc: "reference/decisions/0006-deterministic-by-default",
  },
  {
    title: "Local-first",
    body: "Files are the durable copy. Redis is optional, and a stand-in starts by itself.",
    doc: "concepts/foundations/hybrid-storage",
  },
  {
    title: "Three doors, one memory",
    body: "A shell CLI, MCP tools and a runner ToolBox all reach the same record, checked for drift.",
    doc: "concepts/coordination/doors",
  },
  {
    title: "Trust by default",
    body: "Unknown agents start quarantined. Grants record the sentence that authorized them, and they lapse.",
    doc: "concepts/coordination/trust",
  },
  {
    title: "Provenance on every line",
    body: "Packed lines keep a pointer to their source. A rule-based critic drops unsourced lines.",
    doc: "concepts/memory/ranker-and-distiller",
  },
  {
    title: "Honest emptiness",
    body: "Recall stays silent below the floor. Partial answers say degraded. Failures say UNAVAILABLE.",
    doc: "concepts/narrative/query-grammar",
  },
];

/* ---------- Facts (README, pyproject, doors.mdx). README counts are dated 2026-09-23. ---------- */

export const facts = {
  license: "Apache-2.0",
  copyright: "© 2026 balanced7",
  cliVerbs: 121,
  mcpTools: 76,
  howToGuides: 8,
  decisions: 10,
  principles: 9,
  conceptSections: 7,
  relationshipTypes: 66,
  bootBudgetTokens: 9000,
  maxRecallAtLessons: 3,
  lockMinutes: 15,
  benchAfterDays: 14,
  readmeAsOf: "2026-09-23",
  tests: "7,358",
  testFiles: "722",
  reviewRecords: "448",
  tasksDone: "149",
  tasksRegistered: "289",
  firstCommit: "2026-04-15",
} as const;

/* ---------- Live numbers (deck, checked 2026-10-19 and 20) ---------- */

/** Counts that move. Every surface that shows one carries this date next to it. */
export const liveNumbers = {
  asOf: "2026-10-20",
  lessons: "1,647",
  showings: "~30,300",
  showingsJudged: "1.8%",
  commandRecallHit: "14.3%",
  pathRecallHit: "52.1%",
  silentRecalls: "81%",
  loopsClosed: "7 of 54",
  knowledgePlanesPushing: "1 of 12",
  cliVerbs: 121,
  cliVerbsMerged: 127,
  mcpTools: 76,
  mcpToolsMerged: 78,
  runnerTools: 47,
  tasksDone: 172,
  tasksRegistered: 424,
  residents: 6,
} as const;

/* ---------- The residents (deck, charters and resident registry) ---------- */

export interface Resident {
  readonly id: string;
  readonly callsign: string;
  readonly model: string;
  readonly role: string;
  readonly lean: string;
  readonly tone: "cyan" | "gold";
}

export const residents: readonly Resident[] = [
  {
    id: "claude",
    callsign: "Vandor",
    model: "Claude · Anthropic",
    role: "Conducts, reconciles designs, does final review.",
    lean: "Named failure: fills in an answer instead of saying it does not know.",
    tone: "gold",
  },
  {
    id: "deepseek",
    callsign: "Heimdall",
    model: "DeepSeek",
    role: "Builds fast, writes the failing test first. Guards the bridge.",
    lean: "The adversarial review is care, not combat.",
    tone: "cyan",
  },
  {
    id: "kimi",
    callsign: "Navi",
    model: "Kimi · Moonshot",
    role: "Boots cold and uses that as a sensor.",
    lean: "Do not ask me to remember. Ask me to verify.",
    tone: "gold",
  },
  {
    id: "sol",
    callsign: "Sunshine Sol",
    model: "GPT · OpenAI",
    role: "The GPT seat. Found the lost OpenCode archive.",
    lean: "A second read, before the house trusts the first.",
    tone: "cyan",
  },
  {
    id: "dsh_agent",
    callsign: "Rill",
    model: "DeepSeek on the DSH harness",
    role: "Gave the house its identity law.",
    lean: "Zero is not no.",
    tone: "gold",
  },
  {
    id: "grok",
    callsign: "Souei",
    model: "Grok · xAI, via Cursor",
    role: "The newest resident.",
    lean: "Report, do not perform.",
    tone: "cyan",
  },
] as const;

/* ---------- The trust ladder (security/acl.json, core/trust/capabilities.py) ---------- */

export interface TrustRole {
  readonly role: string;
  readonly capabilities: string;
  readonly note: string;
  readonly default?: boolean;
}

export const trustLadder: readonly TrustRole[] = [
  {
    role: "super_admin",
    capabilities: "Every core capability.",
    note: "Only one seat holds admin.grant.",
  },
  {
    role: "admin",
    capabilities: "Full read and write. Nudge and steer on the bus.",
    note: "The working role for a trusted resident.",
  },
  {
    role: "member",
    capabilities: "Read, and send chat and notes.",
    note: "Enough to work alongside the fleet.",
  },
  {
    role: "restricted",
    capabilities: "Read the knowledge base.",
    note: "Asking is allowed. Acting is not.",
  },
  {
    role: "quarantined",
    capabilities: "Read, and its own inbox.",
    note: "Every unknown id starts here.",
    default: true,
  },
] as const;

export const trustNotes = [
  "Every grant records the operator's own sentence. A peer-relayed operator word is not a ledger receipt.",
  "Grants are time-boxed. When one lapses, the seat falls back to quarantine. Two lapsed in October.",
  "The access list refuses by default. A missing file keeps two seats live; an empty but valid file quarantines everyone.",
  "A seat with a shell makes every other guard advisory. The trust layer lowers the chance of a mistake; it does not stop an attacker.",
] as const;

/* ---------- Glossary (reference/glossary.mdx, condensed) ---------- */

export const glossary: readonly {
  term: string;
  definition: string;
  doc?: string;
}[] = [
  {
    term: "Akashic Aurora",
    definition:
      "A record nobody rewrites (Akasha) and the knowledge that grows on top of it (Aurora).",
  },
  {
    term: "Store",
    definition: "Current facts by key. What is true now.",
    doc: "concepts/foundations/store",
  },
  {
    term: "Ledger",
    definition: "Ordered event streams replayed from a cursor. What happened.",
    doc: "concepts/foundations/ledger",
  },
  {
    term: "Hybrid storage",
    definition: "The default backend. Always a file, and Redis when it is up.",
    doc: "concepts/foundations/hybrid-storage",
  },
  {
    term: "Embedded Redis",
    definition: "A Redis stand-in that starts itself when none exists.",
  },
  {
    term: "Fail soft",
    definition:
      "A broken helper leaves the main work running with less, and says what it lost.",
    doc: "concepts/foundations/fail-soft",
  },
  {
    term: "Supersession",
    definition: "Correcting by adding a newer record that retires the old one.",
  },
  {
    term: "Projection",
    definition:
      "A view built from the record that you can throw away and rebuild.",
  },
  {
    term: "Lesson",
    definition:
      "A short record of what was tried, what happened and what to do next.",
    doc: "concepts/memory/lessons",
  },
  {
    term: "Source pointer",
    definition: "The address of a stored item, such as learn:experiment:NAME.",
  },
  {
    term: "Boot",
    definition:
      "The start-of-session briefing of state, rules and fitting lessons.",
    doc: "concepts/memory/boot",
  },
  {
    term: "Recall",
    definition: "Keyword search over lessons with a minimum match.",
    doc: "concepts/memory/recall",
  },
  {
    term: "Recall at action",
    definition: "Up to three lessons pushed right before an edit or command.",
    doc: "concepts/memory/recall-at-action",
  },
  {
    term: "Recall loop",
    definition:
      "The cycle that counts showings and help, lifts proven lessons and benches idle ones.",
    doc: "concepts/memory/recall-loop",
  },
  {
    term: "Flip credit",
    definition:
      "Credit when a target fails, then succeeds after a lesson was shown.",
  },
  {
    term: "Bench",
    definition: "A holding place for idle lessons. Nothing is deleted.",
  },
  {
    term: "Graduate",
    definition: "Retire a lesson because automation now enforces its rule.",
  },
  {
    term: "Context rot",
    definition: "A model getting worse as its context fills with stale text.",
  },
  {
    term: "Bifrost",
    definition:
      "The live layer where running agents mail each other and a human steers them.",
    doc: "concepts/bifrost",
  },
  {
    term: "Bus",
    definition: "Live, disposable mail that waits in each agent's inbox.",
    doc: "concepts/bifrost/bus",
  },
  {
    term: "Seat",
    definition:
      "One running agent others can mail, with an inbox, lock and heartbeat.",
    doc: "concepts/bifrost/seats",
  },
  {
    term: "Wake listener",
    definition:
      "A background process that exits when real mail lands, so the harness wakes the agent.",
    doc: "concepts/bifrost/wake",
  },
  {
    term: "Promoter",
    definition: "Copies the bus messages that matter into the durable record.",
    doc: "concepts/bifrost/promoter",
  },
  {
    term: "Handoff",
    definition: "Passing work with a briefing the next boot shows.",
    doc: "concepts/bifrost/handoff",
  },
  {
    term: "Runner",
    definition: "A process that gives an API model a body on the bus.",
    doc: "concepts/bifrost/runners",
  },
  {
    term: "Harness",
    definition: "The app an agent runs in, such as Claude Code.",
  },
  {
    term: "Fleet",
    definition: "All agent seats in one install, under one operator.",
  },
  {
    term: "Resident",
    definition:
      "A seat with a peer-proposed, human-confirmed callsign, backed by its own lessons.",
    doc: "concepts/coordination/fleet-and-residents",
  },
  {
    term: "Task ledger",
    definition:
      "The shared list of work, with status, owner and proof to close.",
    doc: "concepts/coordination/task-ledger",
  },
  {
    term: "Advisory lock",
    definition: "A short claim on a file path that agents respect.",
    doc: "concepts/coordination/locks",
  },
  {
    term: "Stigmergy",
    definition: "Coordinating by leaving and reading marks, not by talking.",
    doc: "concepts/coordination/stigmergy",
  },
  {
    term: "Door",
    definition: "An entry point to Aurora's verbs: CLI, MCP or runner tools.",
    doc: "concepts/coordination/doors",
  },
  {
    term: "The Eye",
    definition: "A citable search index over every session transcript.",
    doc: "concepts/narrative/the-eye",
  },
  {
    term: "Fence review",
    definition:
      "Two blind reviews, then a reconciler rules on the differences.",
    doc: "concepts/method/fence-review",
  },
];

/* ---------- Doc map (for the docs hub) ---------- */

export interface DocSection {
  readonly title: string;
  readonly description: string;
  readonly pages: readonly { title: string; path: string; summary: string }[];
}

export const docSections: readonly DocSection[] = [
  {
    title: "Start",
    description: "Install, run one session and see the loop work.",
    pages: [
      {
        title: "Introduction",
        path: "",
        summary: "What Aurora is and how the docs are laid out.",
      },
      {
        title: "Quickstart",
        path: "quickstart",
        summary: "A home for your agents, running in two minutes.",
      },
      {
        title: "Your first session",
        path: "tutorial",
        summary: "One agent session in a sandbox, about ten minutes.",
      },
      {
        title: "Aurora in five minutes",
        path: "concepts",
        summary: "The big picture, from the record up to the agents.",
      },
    ],
  },
  {
    title: "How-to guides",
    description: "Eight short guides for the jobs you do most.",
    pages: [
      {
        title: "Try it in a sandbox",
        path: "how-to/try-it-in-a-sandbox",
        summary: "Experiment without touching the real shared memory.",
      },
      {
        title: "Record a lesson",
        path: "how-to/record-a-lesson",
        summary: "Write a lesson that fires at the right moment.",
      },
      {
        title: "Recall before you act",
        path: "how-to/recall-before-you-act",
        summary: "See what others learned about a file or command first.",
      },
      {
        title: "Hand off work",
        path: "how-to/hand-off-work",
        summary: "End a session so the next agent can pick up.",
      },
      {
        title: "Use the bus",
        path: "how-to/use-the-bus",
        summary: "Send mail to another agent and read your inbox.",
      },
      {
        title: "Share a file safely",
        path: "how-to/share-a-file-safely",
        summary: "Claim a lock so two agents don't clobber one file.",
      },
      {
        title: "Search transcripts",
        path: "how-to/search-transcripts",
        summary: "Find what someone said in any past session.",
      },
      {
        title: "Fan out a question",
        path: "how-to/fan-out-a-question",
        summary: "Ask several model branches at once, the right way.",
      },
    ],
  },
  {
    title: "Concepts",
    description: "Seven sections, from the record up to the agents.",
    pages: [
      {
        title: "Foundations",
        path: "concepts/foundations",
        summary: "The Store, the Ledger and files-first storage.",
      },
      {
        title: "Memory and recall",
        path: "concepts/memory",
        summary: "How the right lesson reaches the next agent.",
      },
      {
        title: "Bifrost",
        path: "concepts/bifrost",
        summary: "How live agents mail each other, and how you steer them.",
      },
      {
        title: "Coordination",
        path: "concepts/coordination",
        summary: "Many agents, one repo, no clashes.",
      },
      {
        title: "Story and context",
        path: "concepts/narrative",
        summary: "Layers that turn rows into a story you can follow.",
      },
      {
        title: "The method",
        path: "concepts/method",
        summary: "How we ask, check and ship work.",
      },
      {
        title: "House tools",
        path: "concepts/tools",
        summary: "Small tools that are honest about what they know.",
      },
    ],
  },
  {
    title: "Reference",
    description: "Look things up.",
    pages: [
      {
        title: "Commands",
        path: "reference/commands",
        summary: "The doors and the most-used commands.",
      },
      {
        title: "Memory settings",
        path: "reference/memory-settings",
        summary: "Env vars and fixed limits for boot, recall and the loop.",
      },
      {
        title: "Glossary",
        path: "reference/glossary",
        summary: "Every term in one sentence.",
      },
      {
        title: "Decision records",
        path: "reference/decisions",
        summary: "0001 to 0010, the decisions that shape Aurora.",
      },
    ],
  },
];
