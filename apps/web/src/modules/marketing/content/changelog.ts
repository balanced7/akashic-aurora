export interface ChangelogEntry {
  readonly title: string;
  readonly body: string;
  readonly area:
    | "Memory"
    | "Bifrost"
    | "Coordination"
    | "Story"
    | "Foundations"
    | "Method"
    | "Tools"
    | "Docs"
    | "Setup";
  /** 1-3 short shas from the Aurora repo that best evidence the entry. */
  readonly commits: readonly string[];
}

export interface ChangelogMonth {
  /** "YYYY-MM" */
  readonly month: string;
  /** A 3-7 word headline for the month. */
  readonly title: string;
  /** 1-2 sentences. */
  readonly summary: string;
  readonly entries: readonly ChangelogEntry[];
}

export const changelog: readonly ChangelogMonth[] = [
  {
    month: "2026-10",
    title: "Runs anywhere, documented in full",
    summary:
      "Aurora left its first machine. It now runs on Linux and macOS with no Redis to install, and a new docs site explains every part.",
    entries: [
      {
        title: "Embedded Redis, nothing to install",
        body: "Aurora now ships its own Redis server, saved to SQLite. If no server answers, Aurora starts it for you.",
        area: "Foundations",
        commits: ["dc057c93", "ca6092d5"],
      },
      {
        title: "Linux and macOS support",
        body: "Fleet repair, the MCP door and wake processes now work off Windows. Machine paths come from environment settings, not fixed drive letters.",
        area: "Setup",
        commits: ["31b785e0", "3507e1ad", "61cefcfd"],
      },
      {
        title: "uv is the default way in",
        body: "The readme, install guide and contributing guide now lead with uv run. Every printed command names a launcher that exists on your system.",
        area: "Setup",
        commits: ["6e896a6b", "e3d612ef", "2e9b71ce"],
      },
      {
        title: "One command installs the hooks",
        body: "A new installer verb sets up Aurora's hooks from one canonical tree. Aurora now says recall at action is armed only when its hook is installed.",
        area: "Setup",
        commits: ["f573697e", "71850339", "98f52706"],
      },
      {
        title: "A docs site for every concept",
        body: "A new docs site maps Aurora's core ideas in a Diataxis layout. It has a quickstart, diagrams and a page per concept.",
        area: "Docs",
        commits: ["9df61ebb", "817789e6", "ce81eb94"],
      },
      {
        title: "Docs checked for plain style",
        body: "A Hemingway-style checker flags long sentences and filler. Pages were corrected against the code and map each idea to terms other agent tools use.",
        area: "Docs",
        commits: ["a9e39217", "cc8908b3", "d3261994"],
      },
      {
        title: "Strict type checks across the code",
        body: "Type checks now cover the core, the CLI, the runners and the scripts. The pass found and fixed missing imports in several commands.",
        area: "Method",
        commits: ["6c2abc61", "96bca41d", "4425d8fd"],
      },
    ],
  },
  {
    month: "2026-09",
    title: "Manuals and a careful web door",
    summary:
      "Agents gained a shelf of reference manuals and one careful door to the web.",
    entries: [
      {
        title: "The web door",
        body: "Agents fetch pages and run searches through one door. Each fetch leaves a receipt, and served text is marked untrusted.",
        area: "Tools",
        commits: ["82820256", "efb89905"],
      },
      {
        title: "Search that tells the truth",
        body: "Search now says when every engine is blocked, instead of reporting an empty web. More search doors are open by default.",
        area: "Tools",
        commits: ["b6b2c576", "696fbfd9"],
      },
      {
        title: "The manuals shelf",
        body: "Reference docs become labelled passages, searched with BM25 in SQLite. Hybrid search, keywords plus meaning, is the default mode.",
        area: "Tools",
        commits: ["722ac288", "c3e4f2c8", "f07253d6"],
      },
      {
        title: "Wake checks who can be reached",
        body: "Boot and the Discord wake path now ask if a seat is reachable, not only alive. Urgent wake tiers no longer starve behind busy ones.",
        area: "Bifrost",
        commits: ["1a4d0a17", "21536fbb", "1856d94f"],
      },
      {
        title: "Publishing needs an explicit flag",
        body: "The mirror tool commits or pushes only when asked with a flag. It lists every commit before a push, and commits record which seat made them.",
        area: "Coordination",
        commits: ["d2a44ac4", "847b00f8"],
      },
      {
        title: "Recall counts what it prevents",
        body: "A new recall-prevention verb reads the outcome log for mistakes lessons may have prevented, not only failures they fixed.",
        area: "Memory",
        commits: ["0345b5c8"],
      },
    ],
  },
  {
    month: "2026-08",
    title: "The Eye opens the archive",
    summary:
      "Aurora learned to read its own history. Fleets also reached across machines and into Discord, and trust gained real checks.",
    entries: [
      {
        title: "The Eye reads every transcript",
        body: "A new indexer turns session transcripts into one searchable record. You can find, zoom, count and trace events across the whole archive.",
        area: "Story",
        commits: ["55e12c30", "4995f268", "b53b6f92"],
      },
      {
        title: "A transcript archive on two disks",
        body: "Transcripts are archived add-only to two physical disks, and a failure is loud. This is the third backup layer.",
        area: "Foundations",
        commits: ["a07f49df", "5697e0cd"],
      },
      {
        title: "A remote bridge between fleets",
        body: "The bridge links fleets on different machines. It has a durable outbox, an inbound gate and a watcher that reports a dead link.",
        area: "Bifrost",
        commits: ["8c3811b4", "09d41f35", "a6400188"],
      },
      {
        title: "Discord rooms join the bus",
        body: "Discord rooms connect to the bus. A mention wakes the named seat, and ambient chat no longer wakes the whole fleet.",
        area: "Bifrost",
        commits: ["a6746d17", "f9d3ac60", "3417ae48"],
      },
      {
        title: "Access grants and a secret gate",
        body: "A grant verb manages access, and a secret gate masks findings before any push.",
        area: "Coordination",
        commits: ["d7d2a7a8", "9c491d09", "bb24d399"],
      },
      {
        title: "Every action beats a pulse",
        body: "Each tool action now beats its seat, so the roster can tell a live seat from a dead one. One liveness verdict serves every view.",
        area: "Bifrost",
        commits: ["887e4e36", "e5cebae3", "e9d3de48"],
      },
      {
        title: "Recall finds the right command",
        body: "Recall now surfaces the command an agent needs at the moment of need, across all 85 verbs of the door.",
        area: "Memory",
        commits: ["d1d1a8f1"],
      },
    ],
  },
  {
    month: "2026-07",
    title: "Bifrost grows into a fleet",
    summary:
      "The bus became a place to run a fleet. A live console, a task ledger and self-healing runners arrived, with a durable SQLite store underneath.",
    entries: [
      {
        title: "Live console and control plane",
        body: "A live console shows agents talking and lets you step in. The control plane adds a human pause and a guard against runaway loops.",
        area: "Bifrost",
        commits: ["5f6b1831", "f21e92e3"],
      },
      {
        title: "Runners that heal themselves",
        body: "Aurora sees when an agent is wedged and revives it by hand, or on its own once you turn auto-revive on. Inbox delivery is now at least once.",
        area: "Bifrost",
        commits: ["65cadbb1", "d5600345", "403084fb"],
      },
      {
        title: "A governed task ledger",
        body: "Work moved into a task ledger with a state machine. A task can now be parked with a reason instead of left to rot.",
        area: "Coordination",
        commits: ["0d84065b", "46ea7b04"],
      },
      {
        title: "Episodes bookend each session",
        body: "Sessions now open and close as episodes. Aurora suggests when to close one, and a session end closes it for you.",
        area: "Story",
        commits: ["ce216f79", "aa34cf01", "cfe40b49"],
      },
      {
        title: "A SQLite store that holds",
        body: "A SQLite store gives Aurora a file tier that many processes can share at once. Backup and restore became WAL-safe before the switch.",
        area: "Foundations",
        commits: ["544f156e", "253bca7f", "e6072211"],
      },
      {
        title: "Recall value you can measure",
        body: "A stats verb shows the recall funnel: surfaced, helped, flips and captured. A nudge at the flip moment asks the agent to record a lesson.",
        area: "Memory",
        commits: ["2a1e296d", "fa07ca72", "ce844dd4"],
      },
      {
        title: "Built is not wired",
        body: "A gate traces imports from real entry points and flags code nothing calls. A parity check keeps the CLI and MCP doors in step.",
        area: "Method",
        commits: ["82e76229", "b982d92a", "328209a7"],
      },
    ],
  },
  {
    month: "2026-06",
    title: "Recall at action and the bus",
    summary:
      "Aurora started to read the right lesson at the moment of action and to learn which lessons help. Agents gained a shared bus, locks and a story of their work.",
    entries: [
      {
        title: "Recall at the moment of action",
        body: "Aurora shows the right lessons when an agent edits a file or runs a command. No LLM sits in the path, and silence beats a weak hint.",
        area: "Memory",
        commits: ["9a1ef562", "665b2dbc"],
      },
      {
        title: "Recall learns what helps",
        body: "Useful lessons rise and noisy ones fade. When a failed step then succeeds, the lessons shown for it earn flip credit with no vote needed.",
        area: "Memory",
        commits: ["53fe10b8", "07f5ad71"],
      },
      {
        title: "The Bifrost bus",
        body: "One Redis Streams bus carries messages between agents. It adds presence, files shared by reference and MCP tools to send and read.",
        area: "Bifrost",
        commits: ["de28c1bf", "06a50571", "83637308"],
      },
      {
        title: "Wake and a terminal console",
        body: "A blocking wait wakes an idle agent when mail arrives. A terminal console lets you watch agents talk and step in.",
        area: "Bifrost",
        commits: ["b8a77d67", "5609990d"],
      },
      {
        title: "Locks and worktrees",
        body: "Each agent works in its own worktree. Advisory path locks with fencing tokens and a compare-and-set store guard against lost work.",
        area: "Coordination",
        commits: ["a68ed419", "262babbb", "6476f5c7"],
      },
      {
        title: "The narrative spine",
        body: "Work becomes a time-ordered story of beats, chapters and themes. A chronicler writes it up, and new themes surface from embeddings.",
        area: "Story",
        commits: ["1be396f2", "873e10c6", "c90d491d"],
      },
      {
        title: "Ready for others to run",
        body: "Aurora gained a license, an install guide and CI. A discover verb tells a new agent what Aurora can do.",
        area: "Setup",
        commits: ["4e5fadcd", "5ebebc25", "aa5b19a8"],
      },
    ],
  },
  {
    month: "2026-04",
    title: "The first foundation",
    summary:
      "Aurora began as a shared Redis stack for several coding agents. The first commits set up storage, messaging and an MCP server.",
    entries: [
      {
        title: "Redis with three copies",
        body: "The first release ran Redis in a high-availability setup with three copies. A sync service kept data in step.",
        area: "Foundations",
        commits: ["7d744adc", "872420a1"],
      },
      {
        title: "Agents send each other messages",
        body: "A first messaging system let several agents talk to each other over Redis.",
        area: "Bifrost",
        commits: ["0554bf2d"],
      },
      {
        title: "An MCP server",
        body: "An MCP server gave agents a standard way to reach the shared stack.",
        area: "Coordination",
        commits: ["ad3501be"],
      },
      {
        title: "Shared project context",
        body: "A project context system let each agent see what the others were doing. A startup guide walked a new agent through boot.",
        area: "Memory",
        commits: ["1937a2cc", "992628c3"],
      },
    ],
  },
];
