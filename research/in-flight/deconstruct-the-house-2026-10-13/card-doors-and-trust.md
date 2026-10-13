# Teardown card: THE DOORS AND TRUST

- **Date:** 2026-10-13 (repo at `7942319e`, 2026-10-13 07:44 -0400)
- **Seat:** claude (Vandor), a workflow subagent seat, read-only on the house
- **Method:** `research/in-flight/deconstruct-the-house-2026-10-13/teardown-card.md` (draft v1): eight rows, every
  claim labelled, loop altitude, the five traps, the Great Sage report
- **Scope:** `agent_cli.py` (the shell door), `ai_setup_mcp.py` (the MCP door), the runner ToolBox
  (`core/comm/toolbox.py`, the third door), `security/acl.json` + `core/trust/*` (grants and quarantine), the Claude
  Code hooks (`scripts/hooks/`, `agent/harness/hooks/`, both `settings.json` files)
- **Footprint (corrected 2026-10-13 after review; this card was not a pure read):** no house file edited except
  this card; no git command that changes anything. The verbs run were `discover`, `doctor` (no `--page`),
  `harnesses`, `stats`, `injections`, `locks`, plus `--help` checks. Four small probe scripts lived in my
  scratchpad and did only reads (`registry.resolve`, AST parse, Redis `XRANGE`/`XREVRANGE`/`TTL`/`TYPE`, the lesson
  loader).
- **Side effects I caused.**
  - **`doctor` is write-capable, and I ran it as if it were a read** (once: Row 2's last row and V7), because the
    brief listed "doctor WITHOUT --page" as a read. It is not one. `cmd_doctor` calls `examine_fleet(...)`
    (`agent_cli.py:5838`), and in every round: page-grade findings "ALWAYS escalate to the pager", the human-facing
    channel, whatever `--page` says (`core/comm/doctor.py:1604-1608`, `:1640-1641`, `:1746-1757`); `_reconcile_pages`
    runs and can retract standing pages and delete their escalation keys (`:1642`, `:1653-1720`); and each agent's
    stall-hysteresis key is set or cleared (`:138-155`, called at `:470-486`).
  - **What it did:** probably no page push. The round's own headline read "0 page-grade", and `_emit_pages` runs only
    when that count is above zero; the two `[page]` grant rows in the body are printed, not sent
    (`agent_cli.py:5947-5958`). **[inferred]** from the headline and the code.
  - **What it may have done:** retracted a page and deleted its escalation key, if one was standing at that moment;
    set or cleared stall keys. **Effect: unknown.** Pages leave no durable record (bus card, I4), so this cannot be
    checked after the fact.
  - Every shell call I made was traced onto the bus and ledgered by the recall hook. The house measured me while I
    measured it.
- **Privacy:** no private plane, memory content, playing data or shader corpus was read. The user-level Claude
  settings were read only for their hook and MCP registration blocks.

Labels used on every claim: **[observed: pointer]**, **[inferred: from what]**, **[unknown: where I stopped]**.

---

## The picture in one paragraph (hardware version)

Think of the house as one memory controller with **four ports** onto the same memory (the lessons, notes, bus and
locks). **Port 1, the shell door** (`py agent_cli.py`), is like a JTAG debug port: whoever holds the cable gets full
access, and it checks nothing about who you are. **Port 2, the MCP door**, is a bridge that mostly forwards to port 1's
own code. **Port 3, the runner ToolBox**, is the user-mode port: it has an MMU (memory management unit) that looks up
your permission bits in `security/acl.json` before letting a write, a command or a lesson through. **Port 4, the bus
API**, is the interconnect fabric. The ACL is the page table. "Quarantine" is the default no-access page. But there is
no secure boot: **an agent's identity is a string it declares for itself**, so the permission bits are only as true
as the name on the request. The house says this about itself, plainly and to its credit (`core/trust/grant_writer.py:3-19`:
"this module is NOT a new security boundary"). The hooks are microcode wrapped around every Claude instruction: a
prefetcher (recall injection), two hardware interlocks (a git staging veto and a peer-lock veto), a performance
counter (outcome credit) and a watchdog (the Stop hook).

---

## Row 1. Purpose

What it is for, and for whom:

- Give every agent in the fleet one way in to the shared memory, whatever harness it runs in: shell, MCP tools, or a
  runner loop **[observed: `AGENTS.md:5-23` "There are TWO doors"; `scripts/checkers/check_door_parity.py:3-9` names FOUR]**.
- Bound what **unattended** seats can do: a runner with no human watching may only write inside its scope, run only
  allowlisted command families, and write lessons only with `kb.learn` **[observed: `core/comm/toolbox.py:1437-1445`
  write scope, `:1782-1791` exec, `:799-812` kb.learn; ACL reason texts at `security/acl.json:76`]**.
- Record Daniel's authority decisions with his verbatim words, a granter, a date and an undo path. Every grant
  record carries a `reason` with quoted operator words **[observed: `security/acl.json:54,76,118,383,443`]**. The
  ACL is as much a **ledger of decisions** as a permission table **[inferred: from the reason fields' content]**.
- Put the right lesson in front of an agent at the moment it acts (recall injection), and stop two specific
  accidents: blanket `git add` and editing a file a peer holds **[observed: `scripts/hooks/claude_pretooluse.py:15-26`,
  `agent/harness/guards.py:14-46`]**.

Outcome that would make it worth keeping: agents of every kind can reach the memory without help; an unattended seat
cannot widen its own authority; the operator can see who may do what and why; recall arrives at the right time
and its value is measured.

What it is NOT for: stopping a hostile process that already has a shell. **[observed: `grant_writer.py:6-19`]**.

---

## Row 2. Observables (measured from outside, not from the house's description of itself)

| what | value | label |
|---|---|---|
| Shell door size | `agent_cli.py` 11,220 lines, 621,150 bytes | observed: `wc -l`, `ls -la` |
| Top-level CLI verbs | 113 | observed: `py agent_cli.py discover` |
| MCP tools | 76 | observed: `grep -c "@mcp.tool" ai_setup_mcp.py` |
| ToolBox verbs | 53 | observed: `check_door_parity.py --report` |
| Parity checker's "CLI" count | 144 (it counts sub-verbs such as `eye trace` as top-level) | observed: same report vs discover's 113 |
| Recall's verb index | 152 entries, 144 unique names, 8 duplicated (`audit, find, list, roster, run, show, stats, triage`) | observed: probe calling `core.recall.at_action.verb_index()` |
| ACL records | 14; vocabulary of 19 capabilities, 5 role templates | observed: `acl.json`; `core/trust/capabilities.py:13-99` |
| Effective roles today | claude super_admin (17 caps); deepseek admin (11); dsh_agent member (8, write unusable); codex_root and gpt-new **quarantined** (expired 193.4 h and 163.8 h before the probe) | observed: probe calling `registry.resolve` |
| User-level hook wiring | 12 commands on 8 events (PreToolUse x4, PostToolUse, PostToolUseFailure, SessionStart, UserPromptSubmit, PreCompact, SessionEnd x2, Stop), all pointing at `E:/AI-Setup/scripts/hooks/` | observed: the user-level `~/.claude/settings.json` hooks block |
| Project-level hook wiring | 3 commands (PreToolUse trace, PostToolUse, Stop) pointing at `agent/harness/hooks/`; 50 permission allow rules | observed: `.claude/settings.json:8-95` |
| MCP registration | project `.mcp.json` entry DISABLED by `.claude/settings.local.json`; live entry is user-level, absolute path | observed: both files + `~/.claude.json` `mcpServers` |
| Hook twins | 7 Claude hooks exist twice; all 7 files differ; 4 differ only in `sys.path` depth, 3 differ in behaviour (trace, pretooluse, userpromptsubmit) | observed: `diff` of each pair |
| Trace ring | 5,009 rows, 4,914 from Claude hooks, spanning 06:01 to 09:24 local today; 0 identical rows within 3 s | observed: `XRANGE bifrost:trace` probe |
| Recall funnel | 1,625 lessons; 28,899 impressions; 548 ever judged (1.9%); useful 509, noise 39; helped 189; value rate 2.4%; last 24 h 657 injections, about 293,484 tokens pushed | observed: `py agent_cli.py stats` |
| Lesson authorship | 60 distinct author ids; **52 not in the ACL wrote 282 lessons (17%)**; author strings include `'kimi '` (trailing space, 2), `rill` (3), `sunshine` (1), `?` (28) | observed: probe over the lesson loader |
| Bus senders since 2026-10-05 12:00Z | 6 ids; only non-ACL sender is `daniil` (the human, via the Discord gateway) | observed: `XREVRANGE` over 73 inbox/broadcast streams |
| Advisory locks | 3 held, all on pytest temp paths, about 60 days old, printed as "ttl 900s", Redis `TTL` = -1 (never expire) | observed: `py agent_cli.py locks`; probe `TTL` |
| Doctor headline vs body | headline "0 page-grade, 0 banner"; body prints 2 `[page]` grant rows and 1 `[banner]` service row | observed: `py agent_cli.py doctor`, a write-capable round (see "Side effects I caused": effect unknown) |

---

## Row 3. Mechanism (how inputs become what we observe)

**3a. The shell door.** `agent_cli.py` is an argparse program: one `add_parser` per verb, one `cmd_*` function per
verb. It takes the agent id as a positional argument or from `AKASHIC_AGENT_ID` **[observed: `cmd_learn` at
`agent_cli.py:619-688` uses `args.agent_id`; `.claude/settings.json:3` sets the env]**. Its write verbs do not ask the
trust layer anything: a grep of `agent_cli.py` for `resolve(` finds only the doctor, grant and grant-listing paths
(lines 5859, 5948, 6379) **[observed]**. `cmd_bifrost_send` has its own non-trust guards: a sender-shape gate
(`agent_cli.py:7013-7017`) and a default reply deadline for asks (`:7079-7081`) **[observed]**.

**3b. The MCP door.** `ai_setup_mcp.py` wraps the CLI's own `cmd_*` functions under a thread-local stdout capture,
running reads concurrently and writes under one lock **[observed: docstring `:3-49`; `learn` tool at `:395-407`
calls `agent_cli.cmd_learn`]**. Two tools check `kb.learn` before writing (`college` `:756-768`, `capture` `:809-815`);
`learn`, `note`, `handoff`, `lock` and `bifrost_send` do not **[observed: grep of `ai_setup_mcp.py` for `resolve(` /
`Cap.` returns only lines 759-815]**. `bifrost_send` here calls `Bus.send` directly, not `cmd_bifrost_send`
**[observed: `:846-861`]**, so it skips the sender-shape gate and the default ask deadline **[inferred: from 3a and 3b]**.

**3c. The runner ToolBox (the third door).** This is where the ACL actually bites. Writes: process flag
`--allow-write`, then in-root and secret checks (`_resolve`, `toolbox.py:410-433`), then a protected-path check for
`security/` and `AGENTS.md` (`:1425-1427`), then `resolve(agent).can_write(path)` failing closed (`:1437-1445`), then
an advisory lock (`:1446-1455`) **[observed]**. Commands: flag, then `resolve().has(EXEC)` failing closed, then a
families-only allowlist for unattended seats (`:1777-1809`) **[observed]**. Lessons: `_kb_write_ok` checks
`kb.learn` and then shells out to the CLI (`:799-825`) **[observed]**. Bus sends: a kind whitelist, no ACL check
(`:1104-1107`) **[observed]**. A quarantined id never gets a runner at all: `may_run_runner` refuses it, and every
runner script calls it **[observed: `registry.py:303-326`; callers in `scripts/bifrost_runner*.py`]**.

**3d. The trust resolver.** `registry.resolve(agent_id, verified=True)` reads `security/acl.json` (mtime-cached) and
returns a Grant: unknown or empty id gives quarantined; unreadable file gives the bootstrap floor (claude super_admin,
deepseek admin, everyone else quarantined) with one loud stderr line; expired grant gives quarantined
**[observed: `registry.py:329-345`, `:39-42`, `:119-140`]**. `verified` defaults to `True` and no caller I found passes
`False` from a real identity check **[observed: call list from grep; unknown: whether any out-of-tree harness does]**.
A record with no `bus_send_kinds` field resolves to "every kind" (`registry.py:167,172`; `can_send_kind` `:71-74`),
which is wider than any role template **[observed]**. `can_write` returns False whenever `path_scope` is empty, even
with the `write` cap (`:62-69`) **[observed]**.

**3e. The hook pipeline (what Claude Code runs around every action).**
- SessionStart: a light boot "whisper" plus recall pre-warm **[observed: `scripts/hooks/claude_sessionstart.py:1-14`]**.
- UserPromptSubmit: plan-time recall, top 2, plus one unread-bus line **[observed: `claude_userpromptsubmit.py:1-30`]**.
- PreToolUse: (1) `claude_trace.py` broadcasts a display-only trace line and a presence beat for every tool;
  (2) `claude_pretooluse.py` for shell and file tools: dedup within 3 s, cwd-drift warning, scope check, then **the only
  two denies** (blanket git staging; a peer's advisory lock, failing closed when the id is unset), then recall-at-action
  context **[observed: `scripts/hooks/claude_pretooluse.py:247-305`; `agent/harness/guards.py`]**; (3) the browser guard
  denies GPU-heavy URLs in the embedded browser **[observed: `claude_browser_guard.py:1-15`]**.
- PostToolUse / PostToolUseFailure: credits a surfaced lesson "helped" when a target fails and then succeeds; the fail
  half is rebuilt from the transcript because PostToolUse never fires on failure **[observed: `claude_posttooluse.py:1-30`]**.
- Stop: blocks a stop when no wake listener is armed; bounces a promise-shaped ending once per session **[observed:
  `claude_stop.py:1-25`]**.
- PreCompact / SessionEnd: drafts a where-we-are file and folds session signals **[observed: `claude_sessionend.py:1-25`]**.
- Every hook fails open; only the two guard verdicts and the browser guard can stop an action, and the Stop hook can
  hold a turn open **[observed: docstrings above]**.

**3f. Registration surfaces.** Hooks and the MCP door each have a project-level registration (relative paths, ships
with the public repo) and a user-level registration (absolute paths, this host). The house chose "single-surface:
user-level" after a double-fire inflated the recall denominator about 2x **[observed: `scripts/hooks/claude_pretooluse.py:38-43`]**.
The project-level MCP entry is disabled; the project-level hook entries are still present **[observed: 3f table rows above]**.

---

## Row 4. First principles (each tested: what law or evidence does it rest on?)

| # | principle | evidence or law | verdict |
|---|---|---|---|
| FP1 | **Identity is self-declared.** An agent id is a string from argv or the environment; nothing authenticates it. | `grant_writer.py:6-9` ("`by` is a plain string"); `resolve(..., verified=True)` default `registry.py:329`; 282 lessons under ids that resolve quarantined (Row 2) | **axiom with evidence** (the law: you cannot authorize what you have not authenticated) |
| FP2 | **A capability exists only where a door checks it.** Deny-by-default is a property of the checking door, not of the ACL file. | enforcement sites: `toolbox.py:806,1440,1786`; `ai_setup_mcp.py:761,812`; `registry.py:316`; `core/screenspace/act.py:476`; none on CLI/MCP learn, note, send | **axiom with evidence** |
| FP3 | **Real authority = the handles a harness gives you.** A seat whose only hands are the ToolBox is bound by the ACL; a seat with a shell holds port 1. | `harnesses`: dsh seat "drives the house CLI"; dsh_agent's `write` is a dead letter at the ToolBox yet the seat writes through its shell; `may_run_runner` | **inferred from evidence**, strong |
| FP4 | **Fail direction is chosen per gate.** Guards fail open so an agent is never bricked; trust checks on write and exec fail closed. | `guards.py:8-10`; `toolbox.py:1443-1445, 1790-1791` closed; `toolbox.py:810-811` (`_kb_write_ok`) **open** on a trust error | **design choice, not a law**; one gate breaks the house's own pattern |
| FP5 | **The operator is the root of trust.** The ACL records his decisions; renewal is not ratification. | reason texts quoting Daniel; `acl.json:332,340` | **axiom by policy** (Daniel's values), cited to `docs/ORG.md` Part 4, which I did not read **[unknown]** |
| FP6 | **The Claude Code hook contract:** exit 0 + JSON `deny` blocks; exit 1 proceeds; PostToolUse fires only on success. | house notes captured from live payloads, fixtures in `tests/fixtures/claude_payloads/` (`claude_posttooluse.py:15-22`) | **observed as documented by the house**; not re-verified against Anthropic's docs in this pass |
| FP7 | **"Unknown agents are QUARANTINED (read-only)"** | stated in `acl.json:2` and `AGENTS.md:8` as a property of the system | **TRAP 1: an assumption dressed as an axiom.** True at the ToolBox, the screen actuator and two MCP tools; false for CLI/MCP `learn`, `note`, `handoff`, `lock`, `bifrost-send` (FP2 evidence; 282 lessons). **Wrong from birth at the shell door, not decayed:** the sentence entered `AGENTS.md` on 2026-08-03 (`6b494b91`), and the shell `learn` has never checked `kb.learn` (`git log -S kb.learn` and `-S KB_LEARN` on `agent_cli.py` both return nothing) [observed, added at review] |
| FP8 | **"The MCP door can never drift from the CLI, because it runs the CLI's code path"** | `ai_setup_mcp.py:7-11` | **TRAP 1 again.** True for `learn`; false for `bifrost_send` (3b). **Wrong from birth for that tool:** the sentence was in the file by 2026-06-28, the day `bifrost_send` was written to call `Bus.send` directly (`83637308`) [observed, added at review] |

---

## Row 5. Capabilities (what we would need to HAVE to build or run this)

- Python 3.11 via `py`; argparse; the MCP SDK (FastMCP) and `anyio` for the MCP door **[observed: `ai_setup_mcp.py:51-69`]**.
- Redis on port 16379 as the live substrate for bus, locks, presence **[observed: probes connected there]**; a file
  fallback when it is down **[observed: `AGENTS.md` "Fail-soft"]**.
- Claude Code's hook events and their payload shapes; Codex and Cursor hook adapters for the other harnesses
  **[observed: `agent/harness/hooks/` listing; `harnesses` matrix]**.
- A recall engine able to rank lessons per action in a hook's time budget **[observed: `core/recall/at_action.py`]**.
- An operator willing to rule on grants, and a super-admin seat to enact them **[observed: ACL reasons]**.
- A naming discipline for agent ids (stable, one per door) **[observed: `acl.json:144` "Distinct id per DOOR"]**.
- Pins that run the real hook file as a subprocess, because mocked pins hide wiring gaps **[observed:
  `tests/test_seat_heartbeat_wiring.py:12-17`]**.
- Search Everything for the `find` verb **[observed: `ai_setup_mcp.py:428-454`]**.

---

## Row 6. Required steps (building it from nothing, and what blocks what)

1. **Shared store + the shell door** (the kernel everything else wraps). Blocks all below.
2. **An identity convention** (`AKASHIC_AGENT_ID`, one id per door). Blocks attribution, locks, grants.
3. **The MCP door** as a wrapper over the CLI functions. Needs 1.
4. **Capability vocabulary + role templates + `resolve()`** failing closed. Needs 2.
5. **ToolBox gates + `may_run_runner`** for unattended seats. Needs 4. *This is the step that makes quarantine real.*
6. **Hook adapters**: scope guard first, then the two vetoes, then recall injection, then the credit loop. Needs 1 and a recall engine.
7. **One registration surface** plus a dedup guard. Needs 6.
8. **Observability**: doctor rows for the ACL floor and expiry, the injection ledger, the stats funnel. Needs 4 and 6.
9. **The grant writer** (atomic, audited) and the instance-local ACL split (t384). Needs 4.

Critical path: **1 → 2 → 4 → 5**. Without 2 there is nothing for 4 to look up; without 5 the ACL is a document, not a
gate **[inferred: from Row 3]**. The house built them in about this order **[inferred: from dates in comments, 07-04
bootstrap to 08-02 write scope; not verified against git history]**.

---

## Row 7. Invariants and failure modes

| invariant | holds? | what a break looks like from outside |
|---|---|---|
| I1 Unknown id resolves quarantined | **holds** [observed: probe, `nobody_xyz` and empty id] | n/a |
| I2 Expired grant resolves quarantined, and doctor says so | **holds** [observed: probe + doctor GRANTS LAPSING] | a seat silently refused; the house fixed the silence (T151) |
| I3 Missing ACL drops to a loud floor | **holds by code** [observed: `registry.py:119-140`]; not exercised live [unknown] | one `[trust]` stderr line |
| I4 Quarantined ids cannot write shared knowledge | **holds at ToolBox and MCP college/capture; does not hold at CLI/MCP learn and note** [observed: 52 unlisted ids, 282 lessons; 12 sampled ids absent from all 45 tracked ACL versions] | lessons from unlisted ids; author-string variants |
| I5 A runner cannot rewrite its own trust or launch surface | **partly.** `security/` and `AGENTS.md` blocked [observed: `toolbox.py:1425`]; `.claude/` **not** in the write guard, although two ACL records say it is [observed: `acl.json:54,444`] and the commit family does block it [observed: `toolbox.py:1716`] | a runner edit to `.claude/settings.json` (where project hooks are registered) would be accepted by the write door [inferred]; no test pins it [observed: grep of `tests/`] |
| I6 Each hook fires once per action | **holds in the 3 h 20 min window I could see** [observed: 0 repeats in 4,914 rows] | doubled trace lines; a funnel denominator about 2x hot (the K0 incident) |
| I7 The two hook copies are the same except for path depth | **does not hold** [observed: 3 of 7 pairs differ in behaviour] | a fix lands on the copy that is not running (the house documented this exact class: `tests/test_pretooluse_twin_strangler_port.py:1-17`) |
| I8 Advisory locks lapse by TTL | **does not hold for 3 keys** [observed: TTL -1, about 60 days, from `tests/test_write_door_acl_scope.py` pins] | `locks` lists stale holders forever; a real future path collision would be refused by a ghost |
| I9 The peer-lock veto separates concurrent sessions | **not between Claude sessions** [inferred: `locks.py` `path_conflict` treats same id as self; the hook passes the shared env id `claude` at `claude_pretooluse.py:240-242`; the trace ring shows several concurrent `claude` sessions] | two Claude sessions edit one file with no veto |
| I10 Recall hints name commands that run | **does not hold** [observed: hook advised `py agent_cli.py trace`; parser rejects it; real command is `eye trace`; root cause `at_action.py:1991-2006` flattens sub-verbs] | an agent runs a dead command and loses a turn |
| I11 The doctor headline reflects the body | **does not hold** [observed: "0 page-grade, 0 banner" over 2 `[page]` + 1 `[banner]` rows] | a glance at the first line says all clear |

---

## Loop altitude (every value chain, and whether the signal flows back)

**L1. The grant loop.** Daniel's word → claude edits `acl.json` with the verbatim reason → `resolve()` → the ToolBox
or screen actuator refuses or allows → the refused agent asks claude on the bus → claude asks Daniel.
*Back-signal:* expiry shows as a doctor `[page]` row **[observed]**. *Actuation:* two grants have sat expired for
about 8 days (codex_root) and 7 days (gpt-new) with no renewal or deliberate revoke **[observed: probe hours]**, against the house's own doctrine
"renew by editing, never by letting it lapse" **[observed: doctor drill text]**. The headline count hides the row
(I11). **Verdict: measured but not actuated; half-open.** The decision itself is Daniel's.

**L2. The recall injection loop.** Lesson → hook injects (plan or action altitude) → agent acts → PostToolUse credits
a flip, or an agent votes → counters → ranking. **Closed but thin**: 1.9% of impressions are ever judged
**[observed: stats]**. The house labels this honestly as coverage-dominated, not a quality verdict **[observed]**.
*Sub-loop, the verb channel:* recall also pushes `[verb]` hints, but `log_injection` returns early when there are no
lesson sources **[observed: `at_action.py:1583-1585`]**, and verb hints carry no source a vote could name.
**Designed-open: actuation without measurement.** That is why the wrong `trace` hint has no path back.

**L3. The quarantine onboarding loop.** New id → quarantined → refusal with a teaching message → the agent asks for a
grant → claude grants. **Closed at the ToolBox** (the refusal text exists, `toolbox.py:808-809`, and the ask path is
reachable because ToolBox sends are ungated, `:1104-1107`). **Never starts at the CLI/MCP doors**, because nothing
refuses there, so ids multiply instead of being registered: 52 unlisted authors, `'kimi '`, `rill`, `sunshine`
**[observed: Row 2; inferred: the causal link]**.

**L4. The hook-twin maintenance loop.** Change a hook → pins → the running copy. **Partly closed**: the PreToolUse twin
has a parity pin and is ported (`scripts/hooks/claude_pretooluse.py:148`) **[observed]**; the UserPromptSubmit plan
path is unported on the live copy and unpinned **[observed: diff; grep of `tests/` for `plan_block`]**;
`check_wiring.py:73-76` walks only the `agent/` copy and calls `scripts/hooks/` "transitional ... deleted at next
session start", yet those are the files this host runs **[observed]**.

**L5. The lock loop.** Acquire with a TTL → work → release at reply or TTL lapse. **Open for keys that lost their
TTL**: nothing I found sweeps a lock with TTL -1 **[observed: 3 such keys; unknown: whether a janitor exists outside
`core/comm/locks.py`, which is where I stopped]**.

---

## Row 8. Verification (predictions that could fail, the test, the result)

| # | prediction (registered before the run) | cheapest test | result |
|---|---|---|---|
| V1 | An unlisted id and an empty id resolve quarantined with only `read` + `bifrost.inbox` | probe `registry.resolve("nobody_xyz")`, `resolve("")` | **held**: role quarantined, 2 caps |
| V2 | codex_root and gpt-new resolve quarantined today (expiry passed) | same probe + `expiring_grants()` | **held**: expired 193.4 h and 163.8 h earlier |
| V3 | dsh_agent's `write` is unusable and its send kinds are wider than its role | probe `can_write("research/x.md")`, `bus_send_kinds`, `can_send_kind("decision")` | **held**: False, ALL, True (member template allows chat and note only) |
| V4 | `security/acl.json` is gitignored, contrary to `registry.py:8` and `acl.json:2` | `git check-ignore -v security/acl.json` | **held**: `.gitignore:225` |
| V5 | The verb the hook advertised, `py agent_cli.py trace`, does not parse | run it with `--help` | **held**: "invalid choice: 'trace'" |
| V6 | Recall's verb index holds more than the 113 real verbs and includes `trace` | probe `verb_index()` | **held**: 152 entries, 144 unique, `trace` present |
| V7 | doctor shows the two expired grants | `py agent_cli.py doctor` (not a read: a write-capable round, effect unknown; see "Side effects I caused") | **held**, plus a surprise: the headline counted 0 page rows |
| V8 | Both hook registrations fire in this repo, so identical trace lines appear in pairs | scan the whole trace ring for identical Claude-hook rows within 3 s | **FAILED**: 0 pairs in 4,914 rows. The project-level hooks did not fire in these sessions. Window: 06:01 to 09:24 today, workflow sessions only |
| V9 | The door-parity gate passes, because it compares names, not behaviour | `py scripts/checkers/check_door_parity.py` | **held**: PASS with 4 known gaps, while 3b shows `bifrost_send` behaves differently on two doors |
| V10 | Ids that resolve quarantined have nonetheless written lessons | probe the lesson loader against the ACL; `git log -p` of the ACL for 12 sampled ids | **held**: 282 lessons by 52 ids; 0 of 12 ever appeared in 45 tracked ACL versions |
| V11 | Non-ACL agents appear as bus senders after Oct 5 | `XREVRANGE` over 73 streams since 2026-10-05 12:00Z | **inconclusive**: the only non-ACL sender was the human operator, through the gateway lane; no agent test case existed in the window |
| V12 | A verb-only injection is not ledgered | `injections --hours 1 --json`; look for my verb-only command vs a control command that carried lessons | **held**: 0 rows vs 1 row for the control |
| V13 | Lock keys carry a Redis TTL, because `LockManager` always sets `ex=ttl` (`locks.py:102,110`) | read `TTL` on each `bifrost:lock:*` key | **FAILED**: all 3 return -1 (no expiry) |

Thirteen run, ten held, two failed, one inconclusive. The two failures taught the most: V8 says the project-level hook
file is dormant here (so the double-fire risk is narrower than the code suggests), and V13 found an invariant the code
promises but the store does not keep.

---

## The five traps, as seen here

1. **False first principles.** "Unknown agents are quarantined (read-only)" (FP7) and "the MCP door can never drift"
   (FP8) are both written as properties of the system. Each is true at some doors only.
2. **Chesterton's fence.** The ungated shell door is deliberate: the shell already holds the file system, so a gate
   there would be theatre (`grant_writer.py:6-19`). The project-level hook and MCP entries exist so a public clone works
   with relative paths **[inferred: from relative vs absolute paths and `.mcp.json` being tracked]**. The
   `scripts/hooks/` twins exist because the user-level registration points at them **[observed]**. None of these should
   be removed on sight.
3. **Reductionism.** An agent's real permission is the product of three things: the handles its harness gives it, the
   door those handles reach, and the string it calls itself. No single part (not even the ACL) holds the answer.
4. **The map is not the territory.** Eight maps disagree with the ground: `registry.py:8` and `acl.json:2`
   ("git-tracked"); `acl.json:2` points to `docs/security-schema-proposal.md`, which is not at that path (it lives under
   `docs/library/`); `agent/harness/registry.py:26` names the `agent/` hooks as the user-global adapter;
   `check_wiring.py:73-76` calls the running copies "transitional"; `tests/test_seat_heartbeat_wiring.py:34-35` says
   the twins differ only by path depth; `acl.json:54,444` claim `.claude/` is write-protected; `locks` prints
   "ttl 900s" over keys that never expire; `capabilities.py:28-31` says screen caps are "granted per seat with a time
   box", while claude holds four of them permanently (`acl.json:22-25,34`).
5. **Goodhart.** The parity gate verifies name parity and reports PASS while behaviour differs (V9). The doctor headline
   counts one section and not the others (I11). The recall funnel resists this trap well: it labels its own value rate
   "COVERAGE-dominated, not a quality verdict".

---

## Unknowns and search boundaries

- **Why the project-level hooks did not fire** (V8). Two candidates: the Agent SDK loads only user settings for these
  sessions, or project hooks need a trust step. I did not test an interactive session. Boundary: the trace ring
  (06:01 to 09:24 today).
- **Whether interactive sessions launched from `E:\AI-Setup` double-fire PostToolUse and Stop.** If they do, the
  "helped" credit and the Stop checks run twice there. The PreToolUse hook has a dedup guard; I did not check whether
  PostToolUse has one.
- **How the three lock keys lost their TTL.** I read only `LockManager.acquire`. I did not search for other writers
  of `bifrost:lock:*`, and I did not check whether the test-isolation flag now covers the lock plane (the keys date
  from about 2026-08-14).
- **Whether the open CLI/MCP write doors are intended for MCP-door agents** (Cursor, Claude Desktop). The design docs
  under `docs/library/` (`20260709_agent-security-schema-design-proposal_cdccf1.md` and siblings) and `docs/ORG.md`
  were not read.
- **Whether codex_root and gpt-new are retired or awaiting renewal.** That is Daniel's knowledge, not the code's.
- **The Codex and Cursor adapters** were inventoried, not read.
- **No pytest run**: it was outside the allowed read set, so pin results are not part of this card.

---

## Proposals (smallest first; each says why the part exists; all wait for Daniel)

1. **Correct the maps (docs only, zero behaviour change).** `registry.py:8` and `acl.json:2` ("git-tracked"; the schema
   doc path); `AGENTS.md:8,19` to say exactly where quarantine binds (ToolBox, runners, screen actuator, MCP college and
   capture) and where it does not; `agent/harness/registry.py:26`; `check_wiring.py:73-76`; the twin sentence in
   `tests/test_seat_heartbeat_wiring.py`. *Why the old words exist:* most were true when written, or true at the
   door their author was looking at. `AGENTS.md:8` was not: it was wrong at the shell door from the day it was
   written (FP7).
2. **Make verb hints name runnable commands.** Record the parent parser in `verb_index` so the hint says
   `py agent_cli.py eye trace`; give `check_door_parity.py` the same fix or label its count "including sub-verbs".
   Pin: every rendered `[verb]` hint parses under argparse. *Why the channel exists:* T311, an agent kept missing verbs
   the door already had.
3. **Ledger verb-only injections** under a pseudo-source like `verb:<name>`, so the channel can be voted on. Closes L2's
   open sub-loop.
4. **Make the doctor headline count every section**, or label it "agents only". *Why the sections are separate:* the
   grants and services rows were added later (T151 and the floor work) on top of FleetDoctor.
5. **Add `.claude/` to the ToolBox write guard** (`toolbox.py:1425`), RED pin first. *Why the guard exists:* "an agent
   cannot escalate its own ACL/launch surface"; `.claude/settings.json` registers commands that run inside the
   super-admin seat. Two ACL records already say this protection exists, and the commit family already enforces it.
6. **Lock hygiene, read-only first:** a `locks` line that flags keys whose Redis TTL is -1. No deletion until the writer
   that drops the TTL is found (the fence: those keys might be someone's deliberate pin).
7. **Hook twins:** add a twin-parity pin for the UserPromptSubmit plan path, like the PreToolUse strangler pin, and
   port in whichever direction Daniel picks (the cwd guard lives only in `scripts/`, the `plan_block` refactor only in
   `agent/`). Do not delete either twin: `scripts/` is what this host runs, `agent/` is what a clone's project
   settings name.
8. **Identity hygiene at the write doors:** trim whitespace and print a one-line notice when a write arrives under an
   id that is not in the ACL ("you are writing as an unlisted id; did you mean `kimi`?"). A notice, not a block. *Why
   the door is open:* the house's success bar is agents preferring the store, and a block could cost contributions.
   Whether the CLI/MCP `learn` door should consult `kb.learn` at all is a design question for Daniel, not a fix.
9. **Grant records needing a ruling:** codex_root and gpt-new (renew, or revoke by editing, per the house doctrine);
   dsh_agent (either give `path_scope` or drop the unusable `write` cap; add an explicit `bus_send_kinds`, because a
   missing field currently means every kind); claude's four permanent screen caps versus the time-box rule in
   `capabilities.py:28-31`.

---

## Great Sage report

> **Notice.** The house has four doors onto one memory, and the ACL is checked on one of them in full: the runner
> ToolBox (`toolbox.py:806,1440,1786`), plus the runner launch check (`registry.py:303-326`), the screen actuator, and
> two MCP tools (`ai_setup_mcp.py:761,812`). The shell door and the MCP `learn`, `note`, `handoff`, `lock` and
> `bifrost_send` tools check nothing about identity. 282 of 1,625 lessons (17%) were written under 52 ids that resolve
> quarantined today. Two grants (codex_root, gpt-new) expired about 8 and 7 days ago, and doctor pages them in its body
> while its headline reads "0 page-grade". The two copies of the Claude hooks differ in behaviour in 3 of 7 pairs.
> The recall hook advised a command that does not exist (`py agent_cli.py trace`). Three advisory locks left by a
> test have no expiry in Redis. The ToolBox write guard protects `security/` and `AGENTS.md`, not `.claude/`.
>
> **Analysis.** The trust system is a cooperative ledger with one hard gate, not a fence around the memory. Identity
> is self-declared (FP1), so the ACL can only bind seats whose sole hands are the ToolBox (FP3, from dsh_agent's unusable
> `write` cap alongside its working shell). The house knows this and says it (`grant_writer.py:3-19`). The trouble is
> the gap between that honest sentence and the confident ones in `AGENTS.md:8` and `acl.json:2` (trap 1). The
> onboarding loop never fires at the open doors, so identities multiply instead of registering (L3, from the author
> census). The verb-hint fault survives because that channel has no ledger and so no feedback (L2, from
> `at_action.py:1583-1585`). Hook twins drift because the checker walks the copy this host does not run (L4, from
> `check_wiring.py:73-76`).
>
> **Unknown.** Why the project-level hooks were silent in the 06:01 to 09:24 trace window; whether interactive
> sessions double-fire PostToolUse and Stop; how three lock keys lost their TTL (I read only `LockManager.acquire`);
> whether the open MCP write doors are intended (design docs and `docs/ORG.md` not read); whether codex_root and
> gpt-new are retired. No pytest was run.
>
> **Proposal.** Smallest first: correct the stale maps listed under trap 4 (docs only); make verb hints name runnable commands; ledger
> verb-only hints; make the doctor headline honest; add `.claude/` to the write guard; flag TTL-less locks before
> touching any; pin and port the UserPromptSubmit twin; add an unlisted-id notice at the write doors; and rule on four
> grant records. No deletions proposed. Each part above has its reason stated.
>
> **Verification.** Thirteen predictions ran. Ten held (quarantine resolution, expiry, the dead `write`, the ignored
> ACL, the phantom verb, the flattened verb index, doctor's grant rows, name-only parity, quarantined authorship,
> unledgered verb hints). Two failed: no hook double-fire in the window seen, and lock keys without the TTL the code
> promises. One was inconclusive (bus senders: only the human appeared). V7's test was a `doctor` round, which can
> write the human pager and retract pages; I ran it as a read, and its effect is unknown (see "Side effects I
> caused" at the top).
>
> **Proceed?** NO, not until Daniel rules. Every proposal waits at his gate, and items 8 and 9 are his decisions by
> nature, not repairs.
