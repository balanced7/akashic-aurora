import type { TerminalLine } from "~/modules/marketing/content/aurora";

/** Use cases. Each capability named here maps to a pillar documented in the Aurora docs. */

export interface UseCase {
  readonly slug: string;
  readonly persona: string;
  readonly title: string;
  readonly summary: string;
  readonly pains: readonly string[];
  readonly helps: readonly { title: string; body: string; pillar: string }[];
  readonly timeline: readonly { when: string; what: string }[];
  readonly shifts: readonly {
    moment: string;
    before: string;
    after: string;
    feeling: string;
  }[];
  readonly terminal: readonly TerminalLine[];
  readonly docs: readonly { title: string; path: string }[];
}

export const useCases: readonly UseCase[] = [
  {
    slug: "one-developer-many-agents",
    persona: "One developer, several agents",
    title: "Stop teaching every agent the same lesson",
    summary:
      "You run Claude Code in one terminal and Codex in another. Each one finds fixes the other never hears about. Aurora gives them one memory and keeps them off each other's files.",
    pains: [
      "Codex hits the bug Claude Code fixed yesterday",
      "Two agents edit the same file and one loses",
      "Rules files grow until nobody reads them",
    ],
    helps: [
      {
        title: "One shared record",
        body: "Every agent learns into and recalls from the same lessons.",
        pillar: "memory",
      },
      {
        title: "Recall at action",
        body: "At most three lessons, right before the edit they fit.",
        pillar: "memory",
      },
      {
        title: "Short file locks",
        body: "A 15-minute claim while an agent edits. Peers wait.",
        pillar: "coordination",
      },
    ],
    timeline: [
      {
        when: "Monday",
        what: "Claude Code finds that a second dev server hangs on a busy port. It runs learn.",
      },
      {
        when: "Tuesday",
        what: "You install the hooks once with aurora hooks install --scope user.",
      },
      {
        when: "Wednesday",
        what: "Codex is about to retry a hung test. The port lesson shows up first.",
      },
      {
        when: "Wednesday",
        what: "The retry passes. The lesson earns flip credit and rises in rank.",
      },
    ],
    shifts: [
      {
        moment: "A known snag",
        before: "Rediscovered by each agent",
        after: "Shown before the retry",
        feeling: "Relief",
      },
      {
        moment: "Two agents, one file",
        before: "Last write wins",
        after: "The edit hook waits for the lock",
        feeling: "Calm",
      },
      {
        moment: "Start of a session",
        before: "A wall of rules",
        after: "A ranked briefing",
        feeling: "Focus",
      },
    ],
    terminal: [
      { kind: "cmd", text: "aurora recall port" },
      { kind: "gold", text: "# 1 lesson(s) matching 'port'" },
      {
        kind: "out",
        text: "  - [uncategorized] port-clash: Use when a server start hangs, before you retry: check the port first. (source: learn:experiment:port-clash)",
      },
    ],
    docs: [
      { title: "Recall before you act", path: "how-to/recall-before-you-act" },
      { title: "Share a file safely", path: "how-to/share-a-file-safely" },
    ],
  },
  {
    slug: "agent-fleets",
    persona: "Fleet operators",
    title: "Run a fleet without losing the thread",
    summary:
      "Many seats, many harnesses, one repo. Aurora gives each agent an inbox, a heartbeat and a place on a shared task list. You watch from a local console and keep the brakes.",
    pains: [
      "You cannot tell a working agent from a stuck one",
      "Work gets done twice, or not at all",
      "Stopping one runaway agent means stopping everything",
    ],
    helps: [
      {
        title: "Seats and liveness",
        body: "Each agent has a name, an inbox, a lock and a heartbeat.",
        pillar: "bifrost",
      },
      {
        title: "Task ledger",
        body: "One list. Each task has an owner and the proof needed to close it.",
        pillar: "coordination",
      },
      {
        title: "Control plane",
        body: "Pause all, interrupt one, or slip one a fact mid-task.",
        pillar: "bifrost",
      },
    ],
    timeline: [
      {
        when: "Hour 0",
        what: "Four seats boot. Each reads the ledger and claims different tasks.",
      },
      {
        when: "Hour 2",
        what: "One seat goes quiet. Liveness flags it as stuck, not working.",
      },
      {
        when: "Hour 3",
        what: "You pause the fleet from the console, steer one seat, then resume.",
      },
      {
        when: "Hour 6",
        what: "Tasks close only with a commit and evidence. Core work gets a second reviewer.",
      },
    ],
    shifts: [
      {
        moment: "Who is doing what",
        before: "Guesswork from chat logs",
        after: "The task ledger",
        feeling: "Clarity",
      },
      {
        moment: "A stuck agent",
        before: "Found hours later",
        after: "Flagged by liveness",
        feeling: "Control",
      },
      {
        moment: "Done",
        before: "Someone said so",
        after: "A commit and evidence",
        feeling: "Trust",
      },
    ],
    terminal: [
      { kind: "cmd", text: "aurora task list" },
      {
        kind: "dim",
        text: "# status, owner and the proof needed to close each task",
      },
      { kind: "cmd", text: "aurora bifrost-pause" },
      { kind: "dim", text: "# freeze the bus; resume or nudge one peer later" },
    ],
    docs: [
      { title: "Bifrost", path: "concepts/bifrost" },
      { title: "Task ledger", path: "concepts/coordination/task-ledger" },
      { title: "Control plane", path: "concepts/bifrost/control-plane" },
    ],
  },
  {
    slug: "long-running-projects",
    persona: "Long projects",
    title: "Pick up where the last agent left off",
    summary:
      "Work that spans weeks outlives any one session. Aurora carries your place forward with handoffs, where-we-are notes and episodes, so the next agent boots into a briefing instead of a transcript.",
    pains: [
      "Every new session spends its first hour catching up",
      "Old chats are too long to reread",
      "Decisions get made twice because nobody wrote them down",
    ],
    helps: [
      {
        title: "Handoff",
        body: "A briefing the next agent sees first at boot.",
        pillar: "bifrost",
      },
      {
        title: "Notes that supersede",
        body: "Same title, newer note. The latest wins, the old one stays.",
        pillar: "memory",
      },
      {
        title: "Episodes and the Eye",
        body: "Titled stretches of work, and a citable search over every transcript.",
        pillar: "story",
      },
    ],
    timeline: [
      {
        when: "Week 1",
        what: "An agent ends its session with wrap and a handoff.",
      },
      {
        when: "Week 2",
        what: "A new agent boots. The handoff briefing shows first.",
      },
      {
        when: "Week 3",
        what: "Someone asks why a call was made. lookback answers from notes and commits.",
      },
      {
        when: "Week 4",
        what: "eye find locates what the operator said, with a session and line address.",
      },
    ],
    shifts: [
      {
        moment: "A new session",
        before: "Reread the old chat",
        after: "Read the briefing",
        feeling: "Momentum",
      },
      {
        moment: "A past decision",
        before: "Lost in a thread",
        after: "A note that supersedes",
        feeling: "Certainty",
      },
      {
        moment: "What was said",
        before: "Memory and guesswork",
        after: "A citable address",
        feeling: "Confidence",
      },
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
    ],
    docs: [
      { title: "Hand off work", path: "how-to/hand-off-work" },
      { title: "Search transcripts", path: "how-to/search-transcripts" },
    ],
  },
  {
    slug: "mixing-api-models",
    persona: "Mixed model teams",
    title: "Put API models on the same bus as your coding agents",
    summary:
      "DeepSeek, Kimi and Gemini can join the fleet through runners, so they read and answer mail like any seat. Ask several models at once, then keep every distinct finding instead of the average.",
    pains: [
      "API models sit outside your agent workflow",
      "Multi-model reviews collapse to whatever they agree on",
      "Helper questions balloon into whole agent runs",
    ],
    helps: [
      {
        title: "Runners",
        body: "A body for an API model on the bus.",
        pillar: "bifrost",
      },
      {
        title: "Ask and fan",
        body: "One-shot helper questions, fanned out in declared shapes.",
        pillar: "method",
      },
      {
        title: "Union, not consensus",
        body: "Keep every distinct finding and check each one.",
        pillar: "method",
      },
    ],
    timeline: [
      {
        when: "Step 1",
        what: "Start a runner so an API model can read and answer bus mail.",
      },
      {
        when: "Step 2",
        what: "Fan a review across lenses with ask --geometry lens.",
      },
      { when: "Step 3", what: "Merge findings by union, then check each one." },
      { when: "Step 4", what: "Close the task with evidence attached." },
    ],
    shifts: [
      {
        moment: "A second opinion",
        before: "Copy and paste between apps",
        after: "Mail on the bus",
        feeling: "Flow",
      },
      {
        moment: "Review findings",
        before: "Only what all agree on",
        after: "Every distinct finding, checked",
        feeling: "Rigor",
      },
      {
        moment: "A quick question",
        before: "A full agent run",
        after: "One ask, one answer",
        feeling: "Speed",
      },
    ],
    terminal: [
      {
        kind: "cmd",
        text: 'aurora ask --geometry lens --preset findings --lens "Where can two writers race?"',
      },
      {
        kind: "dim",
        text: "# Aurora checks the shape of the fan before it spends anything",
      },
    ],
    docs: [
      { title: "Runners", path: "concepts/bifrost/runners" },
      { title: "Fan out a question", path: "how-to/fan-out-a-question" },
    ],
  },
  {
    slug: "auditable-agent-work",
    persona: "Teams that need a record",
    title: "Know who said what, and why it shipped",
    summary:
      "Aurora never rewrites history. Fixes supersede. Claims cite their evidence or say it is missing. Tasks close with a commit and proof. When someone asks what happened, you can show them.",
    pains: [
      "Agent output arrives with no source",
      "Status pages drift from reality",
      "Nobody can say why a change was approved",
    ],
    helps: [
      {
        title: "Append-only record",
        body: "Nobody rewrites an event. A fix is a new record.",
        pillar: "foundations",
      },
      {
        title: "Cite or confess",
        body: "Every claim carries its evidence, or says it is missing.",
        pillar: "method",
      },
      {
        title: "Verification gates",
        body: "A commit SHA and evidence to close. A second reviewer for core work.",
        pillar: "method",
      },
    ],
    timeline: [
      {
        when: "Day 1",
        what: "An agent proposes a task. A person approves it.",
      },
      {
        when: "Day 2",
        what: "Work happens. Each claim carries a pointer to its source.",
      },
      {
        when: "Day 3",
        what: "Two blind reviewers check it. A reconciler rules on the differences.",
      },
      {
        when: "Day 4",
        what: "The task closes with a commit and evidence. The record keeps every step.",
      },
    ],
    shifts: [
      {
        moment: "An agent's claim",
        before: "Trust me",
        after: "A source pointer",
        feeling: "Assurance",
      },
      {
        moment: "A status report",
        before: "Hand-written and stale",
        after: "Generated from the live system",
        feeling: "Honesty",
      },
      {
        moment: "A mistake",
        before: "Edited away",
        after: "Superseded, still on record",
        feeling: "Accountability",
      },
    ],
    terminal: [
      {
        kind: "cmd",
        text: 'aurora fence open T-113 --question "is the router split safe?"',
      },
      { kind: "dim", text: "# two blind reviewers, then a reconciler" },
    ],
    docs: [
      {
        title: "Append-only record",
        path: "concepts/foundations/append-only-record",
      },
      { title: "Verification", path: "concepts/method/verification" },
      { title: "Cite or confess", path: "concepts/method/cite-or-confess" },
    ],
  },
];

export const getUseCase = (slug: string) =>
  useCases.find((item) => item.slug === slug);

/** Fit check: accumulation versus parallelism, honest about when Aurora is not the right tool. */
export const fitQuestions = [
  {
    id: "long",
    question: "Do you work on projects that outlive a single session?",
    yes: 2,
    no: 0,
  },
  {
    id: "peers",
    question: "Do you want the same AI peers working with you over months?",
    yes: 2,
    no: 0,
  },
  {
    id: "inherit",
    question: "Should a lesson one agent pays for reach the next one?",
    yes: 2,
    no: 0,
  },
  {
    id: "disposable",
    question:
      "Do you mainly want disposable workers that start fresh each time?",
    yes: -3,
    no: 0,
  },
  {
    id: "hosted",
    question: "Do you need a hosted service with an SLA today?",
    yes: -3,
    no: 0,
  },
] as const;

/** The two bets, from the lesson the fleet wrote when it compared approaches. */
export const bets = [
  {
    id: "accumulation",
    title: "Accumulation",
    line: "Persistent peers that inherit judgement.",
    body: "The same seats work with you for months. A lesson one pays for surfaces for the next agent standing in the same place, so the team gets better instead of starting over. You pay in curation: the record has to stay honest.",
    fits: [
      "Long-lived work with a changing cast of sessions",
      "A team you want to compound, not reset",
      "Willingness to keep the record clean",
    ],
  },
  {
    id: "parallelism",
    title: "Parallelism",
    line: "Disposable workers that start clean.",
    body: "Fresh workers fan out with no context rot and nothing to curate. They are cheaper to scale and easier to throw away. What one learns does not travel to the next, and that is the point.",
    fits: [
      "One-off jobs with a clear finish line",
      "Scale measured in workers, not months",
      "No shared judgement to carry forward",
    ],
  },
] as const;
