# Integration tiers — what each harness actually delivers

Status: current  (2026-07-09, P4: Harness registry still references; registry wins on disagreement)

> Arc started 2026-07-02 (renamed from "citizenship"). Live matrix: **`py agent_cli.py
> harnesses`** (data: `agent/harness/registry.py` — the single source of truth this doc
> narrates; if they disagree, the registry wins and this doc has rotted).

## Why tiers

Any agent can do any task here (no per-agent ownership), but agents arrive through
different RUNTIMES — Claude Code, Cursor, a bare terminal — and each runtime offers
different seams for the memory loop to plug into. Pretending they're equal produces
silent capability gaps (a Cursor agent waiting for a pre-action warning that can never
come). So integration is graded honestly, tier by tier:

| Tier | Name | The question it answers |
|------|------|------------------------|
| T0 | door | Can the agent reach `agent_cli.py` / MCP at all? |
| T1 | identity | Is `AKASHIC_AGENT_ID` set without human diligence? |
| T2 | session cue | Does the auto-boot whisper arrive at session start? |
| T3 | action recall | Do lessons inject at (or near) the moment of action? |
| T4 | outcome credit | Are FAIL→SUCCESS flips observed and credited? |
| T5 | turn rhythm | Does plan-time recall ride every user prompt? |
| T6 | close | Is a where-we-are draft captured at session end? |

## The architecture rule

**Harness adapters translate JSON; shared code decides policy.** The per-runtime hook
scripts in `scripts/hooks/` stay thin translators — parse their runtime's stdin shape,
call shared functions, emit their runtime's stdout shape. What they share lives in
`agent/harness/`:

| Module | The one thing it owns |
|--------|----------------------|
| `scope.py` | is this action/session THIS repo's business? (global registration stays a silent no-op elsewhere) |
| `context.py` | the auto-boot whisper: what it says, when it stays silent |
| `seen.py` | per-session anti-repeat, shared across altitudes AND harnesses |
| `capture.py` | payload-truth capture (bounded, truncated, kill-switchable) |
| `guards.py` | veto verdicts: blanket git staging, peer locks (incl. RC-01 fail-closed-when-unidentified) |
| `nudge.py` | the JIT learn-nudge rate limit (once per target, session cap, kill switch) |
| `registry.py` | this matrix, as data |

Nothing in `core/` or `agent/` (outside adapters' own files) imports a harness name.
The recall-block *orchestration* (recall→render→seen→impression→ledger) is deliberately
still per-adapter — two copies exist (`claude_pretooluse`, `cursor_posttooluse`); a
third harness triggers the extraction (rule of three).

## Claude Code (agent id: `claude`) — 7/7 automated

Hooks are registered **user-globally with absolute paths**, so they fire for any session
cwd and scope-guard themselves to this repo. The two hard-won mechanisms:

- **T4 via transcript synthesis.** Claude Code fires PostToolUse only for SUCCESSFUL
  calls (pinned live 2026-07-01; fixtures in `tests/fixtures/claude_payloads/`). The FAIL
  half of a flip is synthesized from the session transcript (`is_error` tool_results),
  watermarked per failure id; `PostToolUseFailure` is a complementary fast path, not
  sufficient alone (doesn't fire for built-in tool_use_errors, issue #24908).
- **T5 plan-time recall.** UserPromptSubmit injects the top-2 prompt-relevant lessons at
  the turn's highest altitude, plus a one-line unread-bus cue (silent-at-0). Shared
  anti-repeat with action-time recall; ledgered altitude="plan".

## Cursor (agent id: `composer`) — 6/7 automated, two honest compromises

Wired via project `.cursor/hooks.json` (hook shapes pinned from cursor.com/docs/agent/hooks,
fetched 2026-07-02; payload field names UNPINNED until composer lands live captures —
see `tests/fixtures/cursor_payloads/README.md`).

- **T1+T2 in one hook**: `sessionStart` returns `{env, additional_context}` and the env
  PROPAGATES to all session hooks — identity ships even when the whisper is silent.
- **T3 is one-beat-late** (the first compromise): `preToolUse` is deny-only — it cannot
  attach context on an allow. Recall instead rides `postToolUse`/`postToolUseFailure`
  `additional_context`: in time for the retry after a failure, one beat late otherwise.
  A Cursor agent should NOT expect pre-action warnings; locks still veto pre-action.
- **T4 is cleaner than Claude's**: `postToolUseFailure` is a real, direct fail event —
  no transcript parsing, no watermark. Which event fired travels via argv
  (`--event postToolUseFailure` in hooks.json), immune to payload-shape surprises.
- **T5 unavailable** (the second compromise): `beforeSubmitPrompt` cannot inject context.
  There is no plan-time altitude on Cursor; the composer-turnstart idea is dropped.
- `beforeShellExecution` keeps the C0 git guard (matcher pre-filters `git add|commit`,
  `failClosed: true`) — same rulebook as Claude via `guards.py`, so verdicts can't drift.

## Bare CLI (any agent id) — 1/7 automated, contract-covered

No hooks. `AGENTS.md` is the manual contract: export `AKASHIC_AGENT_ID`, `boot` at start,
`recall-at` before risky edits, `learn`/`recall-feedback` after, `wrap --commit` at end.
The tiers don't disappear — they just cost diligence, which decays; prefer a hooked
harness for long work.

## Verification story (payload-truth discipline)

Assumed payload shapes sank the first credit design (2026-07-01). The rule since:
**capture first, pin, then trust.** Every adapter captures its (truncated, bounded)
payloads to `%TEMP%/akashic_recall/payloads*` before acting on any field; captures get
pinned into `tests/fixtures/<harness>_payloads/` and contract tests assert against the
pins, not assumptions.

- Claude: pinned (2026-07-01/02) — `tests/test_claude_hook_contract.py`.
- Cursor: adapter-level contracts run now; payload pins **skip-with-reason** until
  composer runs a hooked session and copies captures in —
  `tests/test_cursor_hook_contract.py`.

## Adding a harness (the recipe)

1. Read the runtime's hook docs; write down which tiers its seams can honestly carry.
2. Register it in `registry.py` (every tier gets a "how" or a named limitation).
3. Write thin adapters: capture payload FIRST, extract defensively, call `agent/harness/*`
   + core functions, emit the runtime's envelope. Fail open (guards fail closed only on
   unverifiable locks).
4. Fixtures dir + contract test (skip-with-reason until captures are pinned).
5. Update this doc's matrix narrative. If you find yourself writing a third copy of the
   recall-block orchestration — extract it first (the deferred `actions.py`).
