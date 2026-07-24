---
akashic_id: art_20260715_t078-capability-surface-reconciliation-c_6a088d
akashic_sha: abffcc744532
status: draft
type: report
date: 2026-07-15
title: T078 Capability Surface — Reconciliation (claude ⋈ deepseek) — 2026-07-15
gist: "claude-capability-surface-2026-07-15.md (BLIND). Daniel directive: ledger T078. ## The headline The two halves are near-perfectly COMPLEMENT"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T16:10:37"
updated: "2026-07-15T16:10:37"
---
<!-- GENERATED PROJECTION of art_20260715_t078-capability-surface-reconciliation-c_6a088d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T078 Capability Surface — Reconciliation (claude ⋈ deepseek) — 2026-07-15

claude-capability-surface-2026-07-15.md (BLIND). Daniel directive: ledger T078.

## The headline

The two halves are near-perfectly COMPLEMENTARY: his is economics-first (his
platform bills per token; we waste ~75% of prompt spend on re-sent system
prefixes and run the priciest model+thinking for everything), mine is
capability-first (the harness ships subagent fan-out, MCP-native doors, cron
sessions, push notifications, headless mode — all unused). And the strongest
cross-validation a blind fence can produce: **his §3 outside-in guesses about
the claude side are confirmed 10/10 by my half** — every capability he
suspected exists; 8 of 10 are underused today.

## Convergences (independent double-hits)

1. **Model routing by task class** — his C2 ≡ my Tier-2 #6. Both platforms run
   flagship-for-everything; both halves name the same fix shape (routing table
   keyed by message/task class, env-overridable).
2. **Economics visibility is the prerequisite** — his V5/C6 ≡ my #9
   measure-first + the shipped T056 telemetry. No optimization ships without
   its meter.
3. **Conversation/context budgets as a discipline** (his C4 truncation ≡ my
   prompt-caching-aware shape) — pay for what changes, not what repeats.

## Rulings

R1. **Wave order: meters before levers.** His C6 (token dashboard) and the
    T056 join land FIRST; C1-C4 adoption follows with before/after receipts.
R2. **C1 prefix caching is probe-gated** (his own risk note: behavior
    undocumented) — a 1-hour cost probe with the meter from C6, then adopt.
R3. **C7 internal tension flagged**: his §1b says native `tools=[...]` is
    wired, §2 says tool text is hardcoded prompt. The probe resolves which is
    live; if prompt-text, C7 is real savings + reliability.
R4. **The bidirectional fence composes across halves**: my H5 (guarded
    headless `claude -p` in his exec-door families) + his C5 (conversation
    checkpointing) = either agent can invoke the other statelessly and resume
    context. This pair is the deepest structural item; its own mini-fence
    before build.
R5. **First wave for Daniel's gate (curated, not the full 15):**
    | Slice | What | Owner |
    |---|---|---|
    | W1 | C6 token dashboard + T056 join (the meter) | deepseek |
    | W2 | C2 per-kind model routing + C3 thinking gate (the levers) | deepseek |
    | W3 | MCP-native door: finish the server rename, register boot/notes/task/bifrost-send as native tools | claude |
    | W4 | A3 escalation gains PushNotification leg (the pager) | claude |
    | W5 | C1 prefix-caching probe (report, then adopt/park) | deepseek |
    | W6 | Subagent verify panels (fence-lite --panel N) | claude |
    Wave 2 parked: headless-claude+checkpointing (R4 mini-fence), scheduled
    maintenance sessions, worktree pipelines, project skills, C4/C5/C7.

## What deliberately does not change

The method itself (fences, pins, gates) — every slice above is a lever INSIDE
the existing discipline, not a new discipline. Consume path, locks, autopilot
rulings: untouched by all 15 slices.

## Confidence

Complementarity: HIGH (near-zero overlap = the halves measured different true
things). W1/W2/W4: HIGH (config-grade changes with meters). W3: HIGH (server
exists). W5: MEDIUM until probed. W6: MEDIUM-HIGH (harness-native, needs
panel-prompt design). R4 pair: MEDIUM — deliberately parked behind its own
fence.
