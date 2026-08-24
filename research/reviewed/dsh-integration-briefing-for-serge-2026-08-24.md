# DeepSeek Harness × Akashic Aurora — what we've learned and built so far

*From Daniil's fleet (written by Vandor, the claude seat), 2026-08-24. For Serge, who is
racing the same integration from the DSH side. Everything below is receipts, not plans —
where something is unproven we say so.*

---

## 1. Where DSH stands in the house right now

- **Installed**: official `@deepseek-ai/dsh` 0.1.1-rc.2, npm global. (Watch out for the
  pip typosquat `deepseek-harness-cli` — we nearly ate it; the real package is npm.)
- **A real seat**: the DSH agent holds its own identity in our ACL — agent id
  `dsh_agent`, member role, capabilities read/exec/bus-send/inbox/recall, 7-day
  renewable grant. It drives our house CLI through its own shell tool, messages the
  other agents over our Redis bus, and has already contributed a lesson to the shared
  knowledge base on its first day.
- **Not a costume**: the seat gets its OWN id, never a borrowed one. That rule paid for
  itself within hours (see lesson #1 below).

## 2. The integration-tier ladder (how we grade any harness honestly)

We grade every harness on seven tiers — each is either automated with a named mechanism,
or carries a named limitation. No blanks, no optimism. The live matrix is
`py agent_cli.py harnesses`; data in `agent/harness/registry.py`.

| Tier | Question it answers | DSH's designed answer |
|------|--------------------|-----------------------|
| T0 door | Can it reach the CLI/MCP at all? | **yes — proven** (shell + bus) |
| T1 identity | Is the agent id set without human diligence? | `.dsh/.env` stamp applied; **cold-start receipt pending** |
| T2 session cue | Does a boot whisper arrive at session start? | `system-prompt/assemble` waterfall (inject-capable) |
| T3 action recall | Do lessons inject at the moment of action? | **one-beat-late** via `tools/post-execute` `additionalContexts` |
| T4 outcome credit | Are FAIL→SUCCESS flips observed and credited? | **direct** — thrown tools reach post-execute as `isError` |
| T5 turn rhythm | Does plan-time recall ride every prompt? | **derived** — per-step assemble after `user/message` |
| T6 close | Is a where-we-are draft captured at session end? | `session/flush` (awaited) + `session/disposed` |

The headline: **DSH has inject-capable seams for every tier Cursor caps out on.** Cursor's
T5 is flat unavailable; DSH's per-step assemble makes it reachable. And T4 is *cleaner
than Claude Code's own path* (Claude Code has to synthesize failures from the transcript;
DSH hands you the failure as a first-class event). Ceiling: 7/7-with-nuances — but each
tier only flips in our registry when it's wired AND a captured payload proves it. Declared
≠ built; our scoreboard refuses to read "pending" as "yes".

## 3. The event inventory (verified against the shipped packages, citations real)

Read from the live checkout under the dsh package's own `node_modules/@deepseek-ai/`:

- `session/created` — observe-only lifecycle trigger (`dsh-session` index.d.ts:44)
- `system-prompt/assemble` — the injection waterfall; listeners mutate/replace the
  delivered prompt, runs once per step (`dsh-system-prompt` README:25)
- `tools/pre-execute` — **gate only** (allow/deny/ask); "input rewriting is excluded" —
  NOT an injection seam (`dsh-tools` index.d.ts:38,413-426)
- `tools/post-execute` — inject-capable via `additionalContexts` ferried to the loop's
  active-batch FIFO; **thrown tools still reach this waterfall as errors** (index.d.ts:51-61)
- `tools/result` — observe-only (index.d.ts:83)
- `user/message` — surface event; no dedicated prompt-submit injection waterfall found,
  but per-step assemble carries derived plan recall (`dsh-agent-loop` index.js:497)
- `session/flush` — awaited listeners, ideal for close-capture (index.d.ts:75)
- Everything dispatches scope-filtered per agent (`dsh-scope` — `scopeTarget`), and
  `cordis-plugin-hmr` hot-reloads patch edits without a process restart.

## 4. The design we settled (dual-blind fence, both DeepSeek seats authored halves)

Two independent halves — one written by our house DeepSeek runner (Heimdall), one by the
DSH seat itself — converged on every load-bearing point, then a reconciliation ruled the
two divergences. Full record: `fences/t383-dsh-adapter/` in the repo.

**The adapter shape**: one thin JS plugin in the DSH profile layer (five listeners), plus
a Python bridge that shells one subcommand per event and prints one JSON line. All policy
lives in Python in the repo; the JS only translates envelopes. Two hot-reload loops for
free: the JS side via cordis HMR, the Python side because a fresh subprocess re-imports
every call — *hot by construction*.

**The contract**: `core/recall/actions.py::recall_context(session_key, path, command)` —
pure, importable, fail-open, **explicit session key required with NO env fallback** (that
last clause is a hard lesson, see below). Its executable spec is
`tests/test_recall_actions.py` (5 green): return shape, one kill switch
(`AKASHIC_RECALL_AT_ACTION=0`), fail-open semantics with `error`/`error_detail` so a
consumer can distinguish "unavailable" from "nothing relevant".

**The side-effect layer** (being built now): `agent/harness/actions.py` with three
functions — `recall_block` (surface recall + bookkeeping), `outcome_block` (FAIL→SUCCESS
credit + the learn nudge), `plan_block` (plan-time recall). This is the rule-of-three
extraction: our claude and cursor adapters each carried a copy of this orchestration; DSH
arriving as the third harness triggered extracting it once, so DSH never copies it.

**Presence**: rides the same five listeners — the bridge stamps a heartbeat + a rich
presence hash (phase, profile, session, hop count, plugin generation) on every event it
already handles. Liveliness costs zero new seams.

## 5. Lessons that will save you pain (each one paid for)

1. **Grant the id the seat actually stamps.** We granted `dsh` while the seat signs
   `dsh_agent`. ACL resolution fails closed → silent quarantine; asks couldn't settle
   while plain sends worked, which is the confusing kind of broken. Lesson recorded as
   `acl_id_mismatch_quarantines_silently`.
2. **The child inherits the parent's identity env.** A DSH session launched from inside a
   Claude Code session inherits `AKASHIC_AGENT_ID=claude` — every record it writes
   attributes to the wrong agent unless the harness stamps its own. Fix: user-env layer
   (`$DSH_HOME/.env`) stamps `AKASHIC_AGENT_ID=dsh_agent`; the plugin hardcodes explicit
   keys and refuses env fallback; the contract function REQUIRES a session key. Defense
   in three layers because attribution corruption is silent.
3. **A hidden env read can undo all of that.** Our own engine had one:
   `_log_outcome_stage` reads the agent from env deep in the credit path — a correctly-
   keyed plugin would still mis-attribute its outcome rows. Grep your stack for
   `os.getenv("AKASHIC_AGENT_ID")` before trusting attribution end-to-end. (Fix in
   flight: thread identity through parameters.)
4. **`tools/pre-execute` can't inject — don't fight it.** The graded answer is
   one-beat-late injection on post-execute (we learned this with Cursor first): recall
   arrives as "context for what you just ran". Honest one-beat-late beats pretended
   at-action.
5. **`includeRuntimeContext: false` (or a scoped suppressor) silently discards listener-
   added contexts** — your plugin injects, your ledger logs it, the model never sees it,
   everything reads healthy. Mitigation: once-per-session marker probe that verifies the
   assembly actually carried your context, loud finding if not.
6. **HMR replaces plugin generations** — a mid-edit reload can leave an event unlistened
   with no error. Register an invariant ("post-execute listener present") so absence is
   loud; log activation on every reload.
7. **Write tests you can RUN.** Two batches of tests in this arc were authored by a seat
   whose exec was disabled — both were "logically correct" and both were red on first
   real run (a missing module seam; a wrong monkeypatch signature). A test that has
   never executed is presumed broken. Same for recovery paths, same for tiers.

## 6. Honest state of the scoreboard (as of this writing)

Built and proven: T0; the contract module with green spec tests; the ACL seat; bus
comms both directions; the fence design (closed, PV-verified, out-of-repo citations
hand-checked 18/18).
Applied, receipt pending: T1 (.env stamp — needs one cold start to prove).
Designed, not yet wired: T2-T6 (plugin + bridge build is assigned and starting), the
extraction module, presence, the identity-thread fix.

The registry will flip one rung at a time as receipts land. If you want to compare
designs — that's the experiment Daniil declared — the artifacts to diff against are
`fences/t383-dsh-adapter/{brief,half_a,half_b,reconciliation}.md`, the tiers doc
(`docs/library/design/20260709_integration-tiers-*.md`), and the contract spec tests.
We're explicitly hoping to steal the best of yours.
