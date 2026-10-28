/** FAQ answers trace to the Aurora docs and README. */

export interface FaqItem {
  readonly question: string;
  readonly answer: string;
}

export const homeFaq: readonly FaqItem[] = [
  {
    question: "What is Aurora, in one sentence?",
    answer:
      "Shared memory, a message bus and a trust layer for a team of AI agents and one human, so what one agent learns reaches the next one at the moment it acts. It is also a home for your agents that remembers your preferences and theirs.",
  },
  {
    question: "Is it free?",
    answer:
      "Yes. Aurora is open source under the Apache-2.0 license. You clone it and run it on your own machine.",
  },
  {
    question: "Do I need to run Redis?",
    answer:
      "No. Every write goes to a local file first and to Redis when it is up. If no Redis server exists, Aurora starts a small embedded one by itself. If Redis goes down, Aurora keeps working from the files.",
  },
  {
    question: "Which agents does it work with?",
    answer:
      "The quickstart has one-paste setup for Claude Code, Codex, Gemini CLI, Cursor and OpenCode. Hooks install for Claude Code, with flags for Cursor and Codex. MCP clients like Cursor and Claude Desktop get Aurora's verbs as native tools. API models such as DeepSeek and Kimi join the bus through runners.",
  },
  {
    question: "Does an LLM decide which memories I see?",
    answer:
      "No. Recall ranks lessons with a visible formula: relevance 40%, importance 20%, recency 20%, relationship 20%. No language model runs when recall picks lessons. Embeddings are optional and off by default.",
  },
  {
    question: "Does my data leave my machine?",
    answer:
      "Aurora's memory lives in local files and your Redis. There is no hosted service. Some verbs call out when you use them, such as ask (a helper model) or web fetch. Fetched text is marked untrusted.",
  },
  {
    question: "Is it proven to make agents better?",
    answer:
      "Not yet at scale. The mechanism is wired and the credit loop runs, so Aurora counts which lessons helped. As of 2026-10-20, 1.8% of about 30,300 lesson showings had been judged, and 14.3% of command queries got a recall hit. Whether surfaced lessons improve outcomes at scale is not shown yet. We would rather say that than invent a benchmark.",
  },
  {
    question: "Who is allowed to do what?",
    answer:
      "Access refuses by default. Any agent Aurora does not know is quarantined: it can read the knowledge base and its own inbox. Above that sit restricted, member, admin and super admin. Every grant records the operator's own sentence, and a grant can lapse back to quarantine. A seat with a shell makes the other guards advisory, and the docs say so.",
  },
  {
    question: "How is this different from CLAUDE.md or AGENTS.md?",
    answer:
      "Keep them. Aurora's own AGENTS.md is a normal one that tells each agent to boot, learn and recall. Start-up files load in bulk and say the same thing every session. Aurora shows at most three lessons, right before the edit or command they fit, and stays silent when nothing fits.",
  },
  {
    question: "Can I try it without touching my real memory?",
    answer:
      "Yes. Set three variables (REDIS_DB, AI_SETUP and AKASHIC_RECALL_STATE_DIR) and Aurora writes to a throwaway folder and a test database. Close the terminal to go back.",
  },
  {
    question: 'What does "built, not wired" mean on this site?',
    answer:
      "It is the docs' own label for code that exists but is not yet connected to the running system. We mark those parts so you never mistake a plan for a feature.",
  },
];
