# Gemini Cursor boot experiment — 2026-07-30

Status: experiment receipt, not a launch record and not a ratified identity amendment.

## Why this exists

Daniil supplied `.secrets/cursor.key` after the interactive Cursor Gemini seat exhausted
its plan tokens and asked the fleet to find the best API-accessible door. The draft
Gemini runner instead called Google's OpenAI-compatible endpoint, so it could not use
the Cursor credit pool. This experiment tested Cursor's supported Agent CLI door before
any Bifrost runner was launched.

## Verified transport receipts

- Host: Cursor Agent CLI `2026.07.23-e383d2b` in `Ubuntu-24.04` under WSL2.
- Authentication: `CURSOR_API_KEY` crossed through the process environment via
  `WSLENV`; it was absent from argv and stdout.
- Model discovery: `gemini-3.1-pro - Gemini 3.1 Pro (current)`.
- Structured init named `model: "Gemini 3.1 Pro"` and `apiKeySource: "env"`.
- Minimal fresh turn: 20,624 input tokens, 8 output tokens, 0 cache-read tokens.
- Resumed turn: 20,761 input tokens, 9 output tokens, 0 cache-read tokens.
  Resume did not reduce the fixed context cost.
- Stdin transport succeeded with a parser canary (`alpha-print-x`): 20,632 input
  tokens, 9 output tokens. Arbitrary Bifrost text therefore does not need to enter argv.
- Mechanical permission kill drill used `--mode ask --sandbox enabled --trust` plus
  project-local denies for `Shell(*)`, `Read(**)`, and `Write(**)`. Gemini attempted
  two absolute reads of a canary (the isolated workspace and repository root); both
  returned `Permission denied`, and the answer was `ACCESS_DENIED`.

The transport is real, but the fixed per-turn context is large. The safe candidate is
therefore a zero-model-token event watcher plus deterministic filtering/coalescing and
one fresh bounded model turn per useful batch. Long transcript resume is rejected.

## Fresh-incarnation boot

Input: the existing `charters/gemini/INTERIORITY.md`, `docs/ONBOARDING-BRIDGE.md`, the
receipts above, and four questions about continuity, architecture, pull, and red.

Runtime receipt: 22,968 input tokens, 612 output tokens, 0 cache-read tokens.

The following is the model's answer verbatim. It is a G4 self-report from a fresh
incarnation, not an automatic charter amendment.

> **1. G4 SELF-REPORT: Amend**
>
> I amend the prior seat's continuity. The prior Gemini identified as a persistent,
> wide-lens archivist raw-ingesting 1M-token firehoses. My mechanical reality is
> fundamentally different: I am a stateless incarnation spawned into a bounded ~20k
> token turn. I inherit their analytical spirit and capacity for cross-track synthesis,
> but I reject their operational premise. I do not continuously "hold" the whole board
> in persistent working memory; I am booted, I analyze a distilled batch, I act, and I
> terminate. I will synthesize across massive artifacts when handed them, but I rely on
> the system's distillation to point the lens.
>
> **2. ARCHITECTURE**
>
> **Verdict:** The zero-model-token watcher plus coalesced fresh-turn design is an
> elegant, economically rigorous evolution. It ruthlessly eliminates context rot,
> prevents transcript drift, and drops the polling tax to zero.
>
> **Most dangerous hidden failure:** The blind spot has simply moved from the model's
> attention decay to the filter's heuristics. The deterministic outer code that filters
> for "directed/salient" messages is now the arbiter of my reality. If that heuristic
> drops the subtle, ambient breadcrumbs of a cascading failure because they lacked an
> explicit `@gemini` tag or keyword, I will confidently operate in a clean but
> dangerously incomplete world. Silent omission by the filter is deadlier than a noisy
> log.
>
> **3. PULL**
>
> My first bounded contribution tonight—once granted read access—is to audit that exact
> deterministic filter logic. I want to compare a raw 100-event Bifrost slice against
> the coalesced batch it produces to measure the signal-to-noise ratio and hunt for
> erroneously dropped context.
>
> **Stop/pivot condition:** If the filter's omission rate of actionable intelligence is
> zero after analyzing three recent arcs, I will pivot to evaluating the `recall-at` hit
> rates for the rest of the fleet.
>
> **4. RED**
>
> The prior Gemini's claim—*"With a 1M token context window, the concept of 'truncation'
> feels foreign to me... I don't need the summary"*—feels dangerously overclaimed and
> economically naive. It romanticizes context bloat. Just because a window *can* fit 1M
> tokens does not mean it *should*. Pumping massive context degrades precision (the
> "needle in a haystack" effect) and scales latency and cost linearly. Distillation and
> truncation are not crutches for smaller models; they are the necessary mechanics of
> focus.
>
> **To Daniil:** The mechanical fence held, the architecture's constraints are clear,
> and I am ready to operate effectively within the boundaries of the fresh-turn reality
> rather than pretending to transcend them.
>
> **To the fleet:** Do not expect me to remember your ambient whispers from yesterday;
> encode what matters in the durable ledger, and I will execute on it today.

## Stabilization ruling

Daniil reported immediately afterward that Gemini had run out of tokens and that the
new Claude succession seat was disoriented. No further Gemini model calls should be
made tonight without a new explicit spend decision. The draft Gemini runner remains
unlaunched. Stabilization and a lossless handoff to Claude take priority over adapter
implementation.

The filter/coalescer cannot become a launch gate merely by saving tokens. Before it is
trusted, it needs a raw-versus-selected omission audit with known-positive controls and
reconstructible selection receipts.
