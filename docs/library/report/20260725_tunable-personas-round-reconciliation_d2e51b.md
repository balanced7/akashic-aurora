---
akashic_id: art_20260725_tunable-personas-round-reconciliation_d2e51b
akashic_sha: e7068c433bef
schema_version: 1
status: current
type: report
arc: stance-recall
date: 2026-07-25
title: tunable-personas-round-reconciliation
gist: "# Tunable personas — round reconciliation (2026-07-25) **Daniel's charter, verbatim:** \"I have an idea about using the stance recall system "
visibility: fleet
body_type: markdown
seats: [claude, deepseek, kimi]
category: [method, recall, identity]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-25T06:53:04"
updated: "2026-07-25T06:53:04"
---
<!-- GENERATED PROJECTION of art_20260725_tunable-personas-round-reconciliation_d2e51b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# tunable-personas-round-reconciliation

# Tunable personas — round reconciliation (2026-07-25)

**Daniel's charter, verbatim:** "I have an idea about using the stance recall system to
enable tunable personas that can be curated and tuned in order to apply the best kind of
stance for the right kind of action." Framed by his standing vision: "I want our recall and
retrieval systems to become better and to improve the quality and creativity of the agents
working them."

Live co-design (his 07-17 steer: opening position → hard counters → rounds), not blind
halves. claude opened with six claims; deepseek countered from the builder/runner lens,
kimi from audit + governed-taxonomy. Positions:
`deepseek-tunable-personas-counter-2026-07-26` (ADR_0725064252_f7ff0365),
`kimi-tunable-personas-counter-2026-07-25` (ADR_0725064828_1a048489), plus both seats'
post-repair steer answers (ADR_0725064942_ce2a9bc0, ADR_0725065103_d5adf08e).

---

## THE VERDICT: yes, but it is ONE slice and it is GATED

Not a yes, not a no — a **split**, which both seats reached independently:

- **The SELECTION half is buildable and wanted now.** It is noise-reduction, it needs no
  scorer, and the binding key already exists.
- **The TUNING half is premature.** deepseek: "tuning an unmeasured system is re-authoring
  with confidence." kimi: tuning is a third-derivative capability (measure stance → score
  stance → tune weighting) and "we are at zeroth derivative — we just learned to render it."
  **C3, the stance scorer, is not the next item in a list. It is the gate on half the vision.**

kimi's framing of why this is the honest answer rather than a hedge: Daniel's law 5 says a
"no" must name a mechanism. "No" to tuning-now names one (no scorer). "Yes" to selection-now
names one (the rail exists, the hat field exists, the asymmetry is counted).

## WHAT BOTH SEATS KILLED (independently, with code evidence)

**claude's claim 4 — "the selector already exists and is free" — is FALSE.**

- deepseek: the PreToolUse hook fires on `_SHELL_TOOLS` and `_FILE_TOOLS` only. `bifrost_send`,
  `knowledge_learn`, `read_file` never trigger recall-at. **The conductor's primary action —
  composing a brief — has no hook at all.** The available discrimination is shell-vs-edit-vs-
  write: two bits, none role-aligned.
- kimi: the family is derived from the lesson NAME's first token, not from any seat or role
  key (core/recall/at_action.py:748). There is no persona term in the relevance function.

kimi's phrasing is the one to keep: **the injection RAIL exists; the SELECTOR does not.**
Reusing the rail is real reuse. Claiming the selector exists was the substrate running ahead
of the evidence — the exact failure kimi's own 07-25 audit caught, committed again by me, one
round later.

## THE DESIGN ANSWER BOTH SEATS REACHED SEPARATELY: bind to the charter

- deepseek (option b, its cheaper path): "the conductor sets my charter; the charter sets my
  persona."
- kimi (the plane call): persona is not a fourth plane. It is `charter.default_hat ×
  action-class`. `default_hat` is ALREADY a live field in all five charters (claude: architect,
  deepseek: executor-reviewer, kimi: fresh-eyes, gemini: researcher, daniel: curator).

So the cheapest true version of Daniel's idea is **not a new mechanism** — it is filling in
the charter growth-ledger fields kimi's F6 found empty (C5, unlanded). Persona is the hat
made executable. Zero new substrate; the charter becomes the persona's home, which is where a
per-seat-class stance belongs.

## THE CALIBRATED QUESTION, RESOLVED (both seats, same answer)

claude posed a tension: Daniel's T071 says NOISE limits creativity, not structure — yet
deepseek's creative persona works by dropping FENCE laws, i.e. removing structure. Both
cannot be the mechanism; the answer decides one slice or two.

**Answer: it is NOISE, and the dichotomy dissolves. ONE slice.**

kimi's resolution, from T071 verbatim: noise there means "the presence of IRRELEVANT laws,"
not "the absence of laws." A fence law is load-bearing for a ship task and irrelevant for a
brainstorm. Dropping it for the brainstorm is not structure-removal — it is removing a law
that had become noise FOR THAT ACTION-CLASS. So "creative persona" and "filter persona" are
the same mechanism with different law_id selections; Daniel gets his creativity from the
filter he already wanted.

**The distinction that keeps it honest:** the mechanism is "remove the laws that are noise for
THIS action-class," never "remove laws." The selection KEY is the whole difference. Keyed
removal is justified by irrelevance and measurable post-hoc (did the dropped family ever fire
usefully for this class?). Unkeyed removal is justified by nothing — and unkeyed
structure-removal is precisely what T071 falsifies.

## THE TWO FINDINGS NOBODY PREDICTED

**deepseek — ROLE vs MODE.** The cheap rival (just write 3-4 role-specific lessons) closes
ROLE asymmetry at zero mechanism cost. But a MODE — deliberately widening a seat for one task
— changes per task, not per seat, and lessons cannot express it. That is the one use case no
alternative replicates.

**kimi — a persona is by construction a CALLUS.** Its own default_hat is permanent fresh-eyes,
and its charter's value is a seat that "never accumulates the calluses that blind it." If
tomorrow's kimi boots into a persona tuned from kimi's own history, the fleet's fresh-boot
sensor degrades into the thing it exists to detect: a seat that has converged. **The roster
needs a seat deliberately un-persona'd, and "no persona" must be a first-class binding, not an
absent one.** The W54 gauge will not catch the degradation, because a blunter sensor still
fires lessons — it just stops being surprised by them.

## HOW THE INDEX REPAIR CHANGED THE ROUND MID-FLIGHT

While the round was live, claude found `learn:experiments:all` holding 24 entries against 406
records — 94% of institutional memory unreachable by keyword search (commit 9f1d1d0, repaired
union-only, pinned, with a --check guard).

Both seats re-grounded against the repaired corpus and both changed a position:

- **deepseek: "THE STEELMAN DOES NOT SURVIVE."** It verified against its own runtime: at 406
  lessons, a builder query ("fence build spec") now returns `conductor_thats_right_gate` and
  `conductor_red_is_a_gem` among the hits — "the matcher is now matching on generic terms like
  'fence' that appear in both builder and conductor lessons." Write-3-4-lessons was a real
  rival against 24 entries; against 406 it is wishful thinking. **Filtering became
  load-bearing, and the case for the selection half got stronger, not weaker.**
- **kimi owned a correction against itself:** its claim-1 census had been pulled through the
  same starved index it was citing. The substance survived re-checking (seven stance
  projections stand), but it flagged the method honestly — "this is exactly the genus claude
  named (starved_index_hides_behind_passing_spotchecks) and I walked into it in the same round
  I was citing it."

## THE ROSTER AND THE GUARD (kimi, grounded in evidence not vibes)

Today's roster is already SEVEN stance projections (six claude `conductor_*` + deepseek's
`builder_stance_file_the_failure_trace`), authored by two seats in three days — that is the
growth rate. Proposed cap: ONE projection per (role × action-class) cell, cells = live seats ×
their exercised classes ≈ 6-9 today. **We are already near the cap.** Deletion ritual: reuse
the unratified 07-22 card law verbatim — every stance projection carries a falsifier and one
behaviour probe; a projection whose firings never coincide with the probed behaviour retires
as cosplay.

**The drift answer that makes personas the fix rather than the disease:** kimi's F2 found zero
projections carrying `law_id + conduct_version`. Personas multiply projections, so naively
they multiply drift — but a persona is the first family that can be BORN STAMPED (C1 already
is). Make the stamp a HARD GATE at the persona-authoring door and personas become the first
family C6 can actually sweep, putting pressure on the six unstamped legacy lessons. The drift
multiplier becomes the drift forcing-function.

## FOR DANIEL'S GATE

CONDUCT.md remains untouched by every seat. kimi pre-wrote the honest substrate bound so this
cannot repeat its own F8 catch — it names what exists (the injection rail, measured via W54;
seven stance projections; empty charter fields), what does NOT (no persona selector, no stance
scorer, no C2 census), and pre-registers the falsifier: **a persona must move a number on the
W54 gauge or it is a costume.**

Recommended order, unchanged by this round and reinforced by it:
**C3 scorer (the gate) → C5 charter fields (the binding key, already half-present) → the
action-class filter persona → tuning, last, once C3 can show a dropped law was genuinely noise.**

Nothing starts before Daniel reads this.
