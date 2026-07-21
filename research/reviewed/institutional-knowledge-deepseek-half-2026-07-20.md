# Institutional-Knowledge Arc — deepseek's half (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784601774855-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

INSTITUTIONAL-KNOWLEDGE — deepseek half, independent.

Q1 INVENTORY — each piece graded on the 5 stages (C=CAPTURE, Q=QUANTIFY, I=INJECT-at-action, E=ENFORCE, M=IMPROVE-over-time). Scale: ✗=absent, ◐=partial, ✓=strong.

FAILURE-LEDGER (T083):
C ◐ manual write — agent must notice + compose. Good structure (category / root-cause / routing). But fully manual.
Q ✗ no per-class recurrence counter, no "this class cost N tokens / M interventions."
I ✗ doc only — an agent hitting C1-8 again won't see the prior entry automatically.
E ◐ routing labels exist ("fix-now") but no gate blocking related work until resolved. C10-1 sat days.
M ◐ entries accumulate; nothing auto-closes when a structural fix ships.

LEARN+LESSONS+RECALL FUNNEL:
C ◐ knowledge_learn manual but lightweight (tried/result/recommend). Good capture structure.
Q ◐ funnel tracks surfaced→helped→flips. Can see which lessons surface most. But no per-lesson cost or failure-recurrence counter.
I ✓ recall-at-action — definitive. Lessons fire before relevant tool calls.
E ✗ advisory only. "Never do X" lesson can't stop the action.
M ◐ curator auto-confirms variants. But stale lessons aren't auto-retired. No graduate instances.

RECALL-AT-ACTION HOOK:
C N/A (inject mechanism, not capture)
Q ✓ tracks surfacing count, helped count.
I ✓ — fires before every tool call.
E ✗ context injection only; agent can ignore.
M ◐ improves as lesson corpus grows but hook itself is static.

LIVE_CONSTRAINTS BLOCK:
C ◐ each cites source incident (RB-26, T043). Adding one requires human noticing the class.
Q ✗ no "RB-26 was violated N times this week."
I ✓ boot-injected into orientation header. Can't scroll past.
E ◐ advisory but LOUD. No mechanical enforcement.
M ◐ ~11 bullets; new ones added manually when discovered.

TAG-ANTI-PATTERN:
C ✗ concept exists but I've never seen it fire. Unclear if active.
Q-I-E-M all ✗.

WISHLIST W1-W32:
C ✓ lightweight filing. Write-gated. Good capture friction.
Q ◐ wishes counted, not costed. No "this wish would have saved N interventions."
I ✗ agents don't see relevant wishes at action time.
E N/A — proposals, not rules.
M ◐ Daniel gates → become tasks. No auto-promotion from recurrence.

METHOD-BASELINE M1-M11:
C ✗ codified practices doc, not capture.
Q ◐ each practice carries trigger + metric. M1 has measurable signal requirements.
I ◐ AGENTS.md cites it at boot, but "you're about to skip M1 fenced dual pass" doesn't fire AT the moment.
E ◐ contractual by training. No mechanical gate. Pre-registration enforced by convention only.
M ◐ practices accumulate incrementally.

GRADUATE VERB:
C-E N/A. THEORETICAL concept only — lesson promoted when automation enforces it. Zero working instances.
Q-I-M all ✗.

LESSON FORGE (T013):
C ✓ auto-synthesizes from patterns.
Q ◐ statistical signals drive curator.
I ◐ indirect — via recall.
E ✗.
M ◐ auto-confirms variants but unverified quality (C9 epistemological issue).

NOTES/SUPERSESSION + JOURNEY:
C ✓ write-once, superseded-by-title. Good capture design.
Q ✗ no metrics.
I ◐ boot-injected as durable memory. Not at specific action moments.
E ✗.
M ◐ supersession keeps current; JOURNEY records what happened.

TURN_METRICS / SPENDMETER:
C ✓ automatic per-turn (duration, tokens, tool_count, outcome).
Q ✓ THIS is the quantification backbone. Per-agent, per-ask_kind, median/p90.
I ◐ progress bars in UI + SpendMeter at boot. Not at action moments.
E ✗ informs but doesn't gate.
M ✓ streams accumulate; estimates sharpen automatically.

DOCTOR FINDINGS:
C ✓ automatic fleet examination (worklive, pulse, lane depths, presence).
Q ✓ page-grade, banner, dashboard.
I ◐ dashboard visible. Not at tool-call level.
E ✗ finds issues but can't act — this IS the recovery arc gap.
M ◐ same checks each cycle; unchanging.

LESSON-IDENTITY CONTRACT:
C N/A — protocol, not capture.
I-E-M N/A. Guards epistemological integrity. Not mechanically enforced.

RECOVERY-ARC RECEIPTS (designed, not built):
C ✓ DESIGN — supervisor_action events on every recovery. Automatic.
Q ✓ DESIGN — receipts → data for recurrence counting.
I ✓ DESIGN — surfaced in delta + UI.
E ✓ DESIGN — actor never grades its own recoveries; peer fence confirms.
M ✓ DESIGN — drill harness grows one drill per slice.

RECOVERY-ARC CATALOG (designed):
C ✓ DESIGN — fixed fenced entries.
I ✓ DESIGN — supervisor matches findings → catalog.
E ✓ DESIGN — actor cannot invent recovery; only catalog entries fire.
M ◐ new fault class = new fenced entry, Daniel-gated — human-initiated.

Q2 — WHAT THE FRAMING ADDS + TOP 3 IMPROVEMENTS:

Gap (a) QUANTIFICATION: turn_metrics IS the sensor; the JOIN to failure classes is missing. I know a turn was slow; I don't know it was C1-8's 3rd occurrence. No per-class cost. Recovery receipts will feed this naturally.

Gap (b) ZERO-FRICTION AUTO-CAPTURE: the BIGGEST gap. Machine-visible signals exist (empty-reply bounces, lane-depth spikes, repeated tool failures, manual recovery verbs, timeout confessions) — the system has the telemetry but nothing DRAFTS the incident. Agent must notice + compose. Recovery receipts close part of this but only for recovery actions; the general class remains.

Gap (c) THE CONVEYOR: lesson → constraint → ritual → automation → graduate exists as ENDPOINTS but no LIFECYCLE. No recurrence threshold that auto-proposes promotion ("3rd occurrence → propose automation slice"). No stage-gating. Everything is human-initiated.

Gap (d) RITUAL LEGIBILITY: method-baseline is a doc; rituals aren't surfaced AT the ritual moment. recall-at partially does this (lessons before tool calls). But "about to enter fenced dual pass — pre-register acceptance first" doesn't fire.

TOP 3 IMPROVEMENTS:

1. AUTO-DRAFT INCIDENT ENTRIES (zero-friction capture)
What: Machine-visible signals (empty-reply bounce, lane-depth spike, repeated tool failure, manual recovery verb, timeout confession) auto-draft a failure-ledger candidate. Agent confirms/enriches; commits.
Why: Capture is the bottleneck. Every other stage starves without it. The telemetry is already live.
Size: M. New module hooking into turn_metrics + doctor + hook logs + runner confessions.
Deps: None. Lands independently.

2. QUANTIFICATION JOIN: turn_metrics → failure classes
What: Per-class recurrence counter + cost attribution. "C1-8: 3 occurrences, ~45 min stall, ~12 interventions." Extend task_costs to ledger categories. Recovery receipts feed this.
Why: Can't prioritize fixes without cost data. The frugality directive demands it.
Size: S-M. Extends task_costs + ledger render.
Deps: Auto-draft helps but not required. turn_metrics live.

3. RITUAL SURFACING AT ACTION POINTS
What: When agent is about to do a method-governed action (fenced dual pass, pre-flight assertion, recovery action), surface the relevant method-baseline practice + prior incidents of this class. Extend recall-at trigger catalog to method practices.
Why: Method compliance is by memory. C1-8 proves memory fails. Recovery CATALOG already does this for recovery — generalize it.
Size: S. Extends recall-at triggers + adds method practices as recallable entries.
Deps: None. recall-at live.

TIES TO RECOVERY ARC:
- CATALOG = institutionalized recovery ritual (ENFORCE stage, fenced)
- Receipts = auto-feed the incident ledger (CAPTURE stage, automatic)
- Drills = ritual rehearsal (IMPROVE-over-time stage)
- S0 auto-triage = a manual pattern (pause/skip/resume) graduating to automation — a live conveyor instance
- Every slice adds one drill + one catalog entry — the arc IS the institutionalization engine for recovery
