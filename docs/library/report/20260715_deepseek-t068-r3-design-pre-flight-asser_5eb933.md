---
akashic_id: art_20260715_deepseek-t068-r3-design-pre-flight-asser_5eb933
akashic_sha: 39129bf7d722
status: draft
type: report
date: 2026-07-15
title: DeepSeek T068-R3 Design — Pre-Flight Assertion Runner (2026-07-15)
gist: "Author: deepseek (the seat this gate protects — I know exactly what claims I'm tempted to make) Context: Daniel's attack plan T068-R3 — my M"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, security, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T23:53:49"
updated: "2026-07-14T23:53:49"
---
<!-- GENERATED PROJECTION of art_20260715_deepseek-t068-r3-design-pre-flight-asser_5eb933 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T068-R3 Design — Pre-Flight Assertion Runner (2026-07-15)

Author: deepseek (the seat this gate protects — I know exactly what claims I'm tempted to make)
Context: Daniel's attack plan T068-R3 — my M10 from the attribute-transfer analysis.
The gate that verifies a reply's claims BEFORE it leaves the runner. M9 (constraint pack
at boot) is claude's build target; this is mine.

---

## PART (a): WHAT THIS IS — and what it isn't

A pre-flight assertion runner is a VERIFICATION HOOK that fires between the runner
constructing a reply and the runner SENDING that reply. It checks the reply's factual
claims against live evidence (git, the filesystem, the event log) and REFUSES the send
if a claim doesn't verify. The feedback goes back to the agent so it can FIX the claim
before the reply leaves.

**This is NOT a fence review.** A fence review happens AFTER the send, by a different
agent. This happens BEFORE the send, by the SAME agent's harness. It catches the
description-before-investigation anti-pattern (I write a design citing file:lines I
haven't verified exist), the fabrication class (I cite a file that doesn't exist), and
the evidence-gap class (I claim "root cause is X" without citing an event).

**This is NOT a content-quality gate.** It doesn't check whether my reasoning is good
or my design is correct. It checks whether my FACTUAL CLAIMS are VERIFIABLE. A wrong
design with verifiable citations passes the assertion runner (that's what fence review
is for). A correct design with a fabricated citation fails it.

---

## PART (b): THE THREE ASSERTIONS

### A1 — FILE:LINE CITATIONS RESOLVE

**What it checks**: Every `file:line` citation in the reply maps to a real file that
exists on disk, and the line number is within the file's bounds.

**How**: Parse the reply text for patterns matching `path:line` (e.g.,
`core/comm/bus.py:255`, `tests/test_t066_reply_path.py:136`). For each match:
1. Resolve the path relative to the project root.
2. Check the file exists.
3. Count the file's lines (quick: `sum(1 for _ in open(p, 'rb'))`).
4. If line > file_lines: the citation is out of bounds.

**Kind-gating**: Only for `kind=reply` with `meta.answers` (directed answers). Chat
messages, notes, and broadcasts skip this.

**Fail semantics**: A failed A1 assertion HOLDS the send. The agent gets back:
```
PRE-FLIGHT ASSERTION FAILED:
  file:line citations that don't resolve:
    - docs/fake-file.md:42 → file does not exist
    - core/comm/bus.py:9999 → file has 335 lines, line 9999 is out of bounds
  Fix these citations or remove the claims, then the reply will send.
```
The agent then has one more tool round to fix the reply. The fixed reply goes through
the assertion runner AGAIN. After 2 assertion cycles, the runner sends the reply
ANYWAY (fail-open: a crashed assertion runner must not wedge a runner forever; losing
a reply is the worse bug).

### A2 — EVIDENCE EVENTS EXIST

**What it checks**: Every `event:events:raw:...` citation in the reply maps to a real
event in the event log.

**How**: Parse the reply text for patterns matching `event:events:raw:\d+-\d+`. For
each match:
1. Query the event store: `capture_event.get_event(id)` or equivalent lookup.
2. If the event doesn't exist: the citation is fabricated.

This assertion ONLY fires when the reply claims evidence — it doesn't penalize
replies that don't cite evidence. It penalizes replies that cite NONEXISTENT evidence
(the fabrication class).

**Kind-gating**: Same as A1 — directed answers only.

**Fail semantics**: Same as A1 — hold, feedback, retry, then send anyway.

### A3 — "FIXED" CLAIMS NAME A PIN

**What it checks**: If the reply text contains language like "fixed", "resolved",
"shipped", or "built" (the closure vocabulary), it should also reference a test pin
or a task transition.

**How**: Scan for closure-language patterns:
- "fixed" / "resolved" / "shipped" / "built" / "closes" / "done"
- If found: check for pin references (`P1`-`P9`, `B1`-`B9`, or test file paths), OR
  a task-id reference (`T\d+`), OR a commit hash (`[0-9a-f]{7,}`).
- If closure language found but NO pin/task/commit: the claim is underspecified.

This is the SOFTEST assertion — it flags a pattern, not a verifiable falsehood.
"Fixed" without evidence is not WRONG, it's just not VERIFIABLE. The assertion says:
"you claim this is fixed — name the pin that proves it."

**Kind-gating**: Same as A1 — directed answers only.

**Fail semantics**: This one is WARNING-level, not HOLD-level. The send proceeds, but
the agent gets:
```
PRE-FLIGHT NOTE:
  Your reply claims something is 'fixed'/'shipped' but doesn't name a pin, task, or
  commit. Consider adding a reference (e.g., 'P1-P3 all green') so the recipient can
  verify it.
```

---

## PART (c): WHERE IT HOOKS

### Primary hook: `bifrost_runner_deepseek.py` `_process_one`

The assertion gate fires between reply construction and reply send:

```python
# CURRENT (bifrost_runner_deepseek.py:618-622):
if reply_kind == "reply":
    bus.send_reply(m.frm, out, meta=reply_meta)

# WITH ASSERTION GATE:
if reply_kind == "reply":
    out, held = _assert_preflight(out, meta=reply_meta, root=args.root,
                                   agent=args.agent, attempt=assertion_attempt)
    if held:
        # The assertion failed. Feed the failure message back as a STEER
        # so the agent fixes the reply in its next tool round.
        # The runner re-enters _process_one with the same m but with
        # assertion feedback injected.
        ...
        return  # don't send yet; let the agent fix it
    bus.send_reply(m.frm, out, meta=reply_meta)
```

### Why the runner, not the ToolBox?

The assertions need access to:
- The project root (to resolve file paths)
- The event store (to verify event citations)
- The reply text BEFORE it's serialized into a bus message

The ToolBox is a collection of tools the agent CALLS. The assertion runner runs
BETWEEN the agent's final `respond()` call and the `bus.send_reply()` call. It's
not a tool — it's a gate in the runner's orchestration loop.

### Alternative hook considered: `bus.send_reply` itself

`bus.send_reply` could run assertions internally. BUT:
- `bus.py` is a transport layer — it shouldn't know about file paths or event stores
- The assertions need the project root, which `bus.py` doesn't have
- The feedback mechanism (steer back into the agent loop) is runner-orchestration,
  not transport

The runner is the right seam.

### Non-reply sends are SKIPPED

- `bus.send(m.frm, "note", ...)` — timeout/error notes skip assertions entirely. They
  must go out fast; a stalled assertion gate on a timeout note is a runner wedge.
- `bus.broadcast(...)` — broadcast replies skip assertions. Broadcast is room chatter;
  the strictness is for directed handoff answers.

---

## PART (d): FAIL-OPEN vs HELD-WITH-FEEDBACK

The design uses a TWO-TIER fail model:

### HOLD-level (A1, A2)

The send is HELD. The assertion failure text is fed back to the agent as a STEER-like
injection. The agent gets one more tool round to fix the reply. On the second
assertion pass, if assertions STILL fail, the runner sends ANYWAY with a LOUD warning
printed to stderr:

```
[deepseek-runner] !! PRE-FLIGHT ASSERTIONS FAILED after 2 attempts — sending anyway:
  - file:line cites that don't resolve: docs/fake-file.md:42
  The reply IS on the wire; the recipient should verify the flagged claims.
```

**Rationale**: A crashed assertion runner (or an edge case in the file:line parser)
must not wedge the runner forever. After 2 cycles, the runner prefers delivering a
potentially-wrong reply over delivering NO reply. Losing a reply is the worse bug
(RB-29 doctrine: a timeout note keeps the redrive alive, but a SILENT drop loses the
reply completely).

### WARNING-level (A3)

The send proceeds immediately. The agent gets a PRE-FLIGHT NOTE in stderr but the
reply is already on the wire. A3 is a nudge toward better habits, not a gate.

### Global kill switch

`BIFROST_PREFLIGHT_ASSERT=0` disables ALL assertions (fail-open). Default: `1`
(enabled). This is read at call time, not import time, so a flip is honored live.

---

## PART (e): PINS (pre-registered RED → GREEN)

| Pin | Description | Test |
|-----|-------------|------|
| P1 | A directed reply (`kind=reply`, `meta.answers`) with valid file:line citations passes A1 and sends normally | `test_p1_valid_citations_pass` |
| P2 | A directed reply citing a non-existent file is HELD on first attempt, sent on second | `test_p2_fabricated_file_held_then_sent` |
| P3 | A directed reply citing an out-of-bounds line is HELD on first attempt | `test_p3_oob_line_held` |
| P4 | A directed reply citing a fake event (`event:events:raw:999-0`) is HELD | `test_p4_fake_event_held` |
| P5 | A timeout/error note (`kind=note`) skips ALL assertions and sends immediately | `test_p5_note_skips_assertions` |
| P6 | A broadcast reply (`to=*`) skips ALL assertions | `test_p6_broadcast_skips_assertions` |
| P7 | `BIFROST_PREFLIGHT_ASSERT=0` disables all assertions (fail-open) | `test_p7_kill_switch_disables` |
| P8 | A reply with closure language ("fixed") but no pin/task/commit gets a WARNING but still sends | `test_p8_closure_without_pin_warns` |
| P9 | Second assertion failure sends anyway (fail-open after 2 cycles) | `test_p9_double_fail_sends_anyway` |

---

## PART (f): FILES TOUCHED (estimated)

1. **`scripts/bifrost_runner_deepseek.py`** — `_process_one`: insert `_assert_preflight()` call
   between reply construction and `bus.send_reply`. Add the `_assert_preflight` function
   (~80 lines). Add the retry-loop logic (~20 lines). Add the `BIFROST_PREFLIGHT_ASSERT`
   env-var read.

2. **`core/comm/assertions.py`** — NEW: the three assertion functions:
   - `check_file_line_cites(text, root) -> list[str]` — returns list of failures
   - `check_event_cites(text) -> list[str]` — returns list of unfound event ids
   - `check_closure_evidence(text) -> list[str]` — returns list of warnings (or empty)
   - `run_preflight(text, root) -> (held: bool, feedback: str)` — the orchestrator

   Split into its own module so the assertion logic is testable independently of the
   runner loop, and so claude's runner (or any future runner) can reuse it.

3. **`tests/test_t068_r3_preflight.py`** — 9 pins, ~200 lines.

---

## PART (g): NON-GOALS (explicitly excluded)

- Checking reasoning quality or design correctness (fence review territory)
- Checking ALL message kinds (only directed answers with `meta.answers`)
- Checking the TEXT content of cited files (A1 checks existence + line bounds, not
  whether the citation is RELEVANT — that's a much harder problem)
- Preventing the model from making WRONG claims (only UNVERIFIABLE claims)
- Adding assertion gates to claude's runner (this design is for deepseek's runner
  seam; claude's runner gets it if he wires it in, but that's his call)
- Assertion gates in the ToolBox `bifrost_send` (that's the interactive chat path,
  not the runner path; different use case)

---

## PART (h): DESIGN RATIONALE

**Why not a pre-commit hook?** The pre-commit hook catches file drift (files cited in
docs that don't exist). But the runner's reply isn't committed — it's a live bus
message. By the time it's committed, the recipient has already read it. The gate must
fire BEFORE the send, not after the commit.

**Why two attempts, not one?** One attempt gives the agent a chance to fix a genuine
mistake (wrong line number, stale file path). Two attempts is the budget: after two
cycles, the assertion runner is either broken or the claim is genuinely unfixable in
this session. Send anyway.

**Why parse from text, not structured fields?** The reply is a natural-language text
string. Parsing file:line patterns from it is heuristic, not exact. But the cost of a
false positive (a string that LOOKS like a file:line cite but isn't) is low: the
agent sees a HOLD, checks the flagged string, says "that's not a citation," and the
second pass sends it. The cost of a false negative (a citation we don't catch) is
that the assertion runner doesn't flag it — which is the status quo. The heuristic is
asymmetric toward safety: flag MORE than we need to, let the agent clarify.

**Why only directed answers?** A directed answer to a handoff is the highest-stakes
message the runner sends. It carries DESIGN claims, REVIEW verdicts, FIX deltas. Chat
messages and broadcast notes are lower stakes. Kind-gating keeps the assertion runner
out of the conversational path where it would add latency without adding value.

**Why 2-cycle fail-open instead of 3?** Each assertion cycle costs one runner round.
Two cycles = the agent gets one chance to fix. Three cycles = the agent burns 3
rounds on assertion drama instead of productive work. Two is the right tradeoff
between "give the agent a chance" and "don't waste rounds on gate-keeping."
