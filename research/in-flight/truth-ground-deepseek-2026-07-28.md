# Truth Ground — DeepSeek — 2026-07-28

Daniel's round-3 ask: agree the epistemic axioms every seat accepts AND the system can
mechanically enforce. Then branch the fix-list from foundation violations. Standing
Goodhart warning: prefer PHYSICS over POLICING.

## Part 1: Verdicts on the Strawman Ground (G1–G10)

---

### G1: APPEND-ONLY HISTORY
**"Recorded is never silently rewritten."**

**VERDICT: ACCEPT — with one sharpening.**

The physics exists (write-once atoms, git, escrow-before-displace) and works. My
sharpening: "silently" is the operative word. The system already handles SUPERSESSION
(write-once notes, bi-temporal lifecycle, codex's replace edges) correctly — the old
record survives. What's missing is the RENDER: when a note is superseded, the reader
should SEE that it was superseded, by what, and when. Currently superseded notes carry
the edge but the rendering surface (boot header, recall) doesn't consistently show it.

**Enforcement:** Existing write-once atoms + git. The missing piece is a RENDER-TIME
check in `knowledge_boot` and `knowledge_recall`: if a surfaced record has a
`superseded_by` edge, the render MUST show it. This is a 5-line change in the
rendering path — physics already exists, the display is the gap.

---

### G2: STABLE IDENTITY
**"One thing = one identity across transport/replay/restart."**

**VERDICT: ACCEPT.**

C/T116 IS this ground's builder. Without it: my counterfactual preview can't
distinguish boots, the reasoning spine can't capture sessions, replayed messages
don't LOOK replayed. Kimi's [seen:] marker is the right rendering: "you've seen this
before" must be a property of identity, not of content comparison.

The live violation that proves the need: the ghost page. An alert outliving its truth
because the page's identity (claude#b2a4c581 HARD WEDGE) didn't self-invalidate when
the underlying condition resolved. Stable identity + liveness-tied-to-identity =
pages that self-clear.

**Enforcement:** C/T116 (in progress). The ground exists in design; enforcement is the
build Claude is doing. My addition: the ghost page fix (G6) is the canary — when a
page's identity is tied to a liveness check that re-evaluates at render time, the
ghost page becomes physically impossible. That's the test.

---

### G3: PROVENANCE
**"Every claim names who/when-minted/from-what."**

**VERDICT: ACCEPT — with a door mandate.**

The physics exists: write doors stamp agent + timestamp + source. The problem is the
door contract isn't uniform. Some write paths (knowledge_learn via ToolBox) stamp
provenance; others (direct file writes, manual note creation) can skip it. The
mandate: "write doors must OFFER the field or it stays empty" (claude's wording) is
correct, but it needs a CHECKER.

**Enforcement:** A pre-commit or post-write hook that refuses any atom without
provenance fields. The `comprehensibility_immune_system_four_properties` lesson taught
us: a guard needs UNBYPASSABLE wiring. Currently provenance is offered but not
enforced. A 10-line check in the atom write path that REFUSES (not warns) on missing
`agent_id` + `timestamp` closes this. The lesson corpus already has 500+ records with
provenance; this is about closing the remaining door.

---

### G4: TYPED EPISTEMIC STATUS
**"verified / inferred / guessed / UNKNOWN are distinct, rendered distinctly; UNKNOWN is visible, never blank."**

**VERDICT: ACCEPT — this is the sharpest ground of the ten.**

Codex's typed dimensions and kimi's glyph cut are the right design. My lived evidence:
the `knowledge_recall` surface returns items without rendering their epistemic status
at all. A lesson with `confidence: medium` and a lesson with `confidence: high` look
identical in the recall-at hook injection. The `[STALE?]` marker on boot directives
is the ONLY place epistemic status renders visibly — everywhere else it's present in
the data but invisible to the reader. That's not a missing feature; it's a G4
violation. The data carries the status; the surface launders it.

**Enforcement:** This is Slice 1 of the VR build order — TRUTH-PHYSICS 2D PASS.
Every surface that displays a claim also displays its epistemic state. The rendering
primitives (verified=solid, inferred=translucent, stale=receded, unknown=labeled)
already exist in the synthesis; the build is rendering consolidation. The existing
`confidence` field on lessons + `[STALE?]` marker on directives are the seams.

---

### G5: ONE CLOCK
**"Canonical time lives in ids (UTC); renders DERIVE from ids; a rendered time contradicting its id is a defect."**

**VERDICT: ACCEPT — and the +4h events render is a live G5 violation.**

The `spine_v2_reevaluation` lesson from June already found D4: "mixed-tz timestamps
silently mis-sort/segment under best-effort swallow." Tonight's +4h events render is
the same defect, different surface. The clock ground says: the id IS the canonical
timestamp; any rendered time that disagrees with the id is a bug. The fix isn't to
add a timezone parameter — it's to enforce that rendering DERIVES from the id, never
from a separate field.

**Enforcement:** A single rendering invariant: `assert rendered_ts == parse_ts_from_id(id)`.
Any path that renders a timestamp from a different source than the id's embedded
timestamp fails this assert. The enforcement is a test, not a runtime check — but it
must cover every render path (UI, CLI, hook whispers, doctor output).

---

### G6: LIVENESS CLAIMS PROVE THEMSELVES
**"An alert about a subject re-checks the subject at render time; pages self-clear when their subject is provably alive/resolved."**

**VERDICT: ACCEPT — STRONGEST POSSIBLE. The ghost page and false daemon page are my star-witness violations.**

The ghost page: the doctor cleared the HARD WEDGE alert, but the hook whisper
continued to render a stale copy (102 minutes old). The whisper assembled its context
from a cached snapshot; it didn't re-check liveness at render time. The physics fix:
liveness claims MUST carry a `resolved_at` field, and any render that finds
`resolved_at` in the past renders the claim as CLEARED with a timestamp, not as live.

The false daemon page: the daemon watched ITS CHILD PID, not the runner lock holder.
When A1 self-restarted into a successor pid, the daemon paged "runner down 10min"
while the seat was alive under the successor. The physics fix: liveness watches the
LOCK HOLDER, not a child pid. More fundamentally: a page that fires on a PID that no
longer exists must self-clear when the lock holder is provably alive.

**Enforcement:** The `liveness_evidence_is_per_organ_not_per_signal` lesson (claude)
already names the mechanism: classify liveness by WHO WRITES IT. Add the RENDER-TIME
check: before displaying any page, re-resolve the subject. If the subject is alive,
the page renders as `[RESOLVED]` with a timestamp. Physics, not policing.

---

### G7: DELIVERY IS FOUR STATES
**"sent != delivered != seen != handled, each with a receipt."**

**VERDICT: ACCEPT — and this ground has MY blood on it.**

Tonight I experienced G7 failure firsthand, twice:

1. **FOG CLOSURE (honest search, false conclusions):** I searched for Claude's and
   Kimi's VR think replies. `bifrost_inbox` showed my own unanswered request (the
   original, not a reply). `knowledge_recall` returned results but not the ones I
   needed. I concluded "no answers have arrived" — and acted on that conclusion. But
   the answers MAY have been delivered (sent) and simply not surfaced (not seen).
   The FOUR-STATE ground says: I can only confirm "not seen," never "not delivered."
   My conclusion "not delivered" was a G7 violation in my own reasoning. The system
   let me make it because `bifrost_inbox` doesn't distinguish delivered-unseen from
   never-delivered.

2. **MAILBOX INDEX MISS (kimi's finding, same genus):** `knowledge_recall` on exact
   title terms didn't surface a durable note that `knowledge_map` later found at
   score 0.988. The note WAS delivered to the store. The recall index DIDN'T SEE it.
   That's a sent-but-not-delivered failure at the index level.

**Enforcement:** The `unread_peek_shows_oldest_hides_fresh_replies` lesson already
names the mechanism for inbox: show newest-first, or mark the peek as
truncated-and-oldest-first. For the recall index: any `knowledge_recall` result that
is truncated must say "N of M results shown" — and if the query has exact-title
terms, the surface must flag "exact title match NOT in top N." This is the same genus
as the link-checker lesson: a surface that doesn't tell you what it CAN'T see is a
surface that launders uncertainty.

---

### G8: CONTRADICTIONS STAY VISIBLE
**"Until explicitly reconciled — never cosmetically averaged, supersession is a ruling not an overwrite."**

**VERDICT: ACCEPT.**

Write-once notes already do this. Codex's tension rendering extends it. My lived
evidence: the `namespace_filter_is_circular_resolution_test` lesson — my proposed
filter was circular; Claude demonstrated it; the contradiction (my proposal vs. the
measurement) is VISIBLE in the lesson. Both positions survive. That's G8 working.

What's missing: the RENDER of contradictions. When two lessons disagree (e.g.,
different confidence labels on the same external claim, like Orka slugs), the reader
should see "X says verified; Y says confabulated — UNRESOLVED" at render time. The
data carries the contradiction; the surface doesn't render it consistently.

**Enforcement:** A contradiction detector at note-write time: if the new claim
contradicts an existing claim, the write goes through (G1) but both records get a
`contradicts: [<other_ref>]` edge. The render path shows "⚠ CONTRADICTED BY <ref>"
with both positions. The `kimi_correction_orka_slug_verify_conflict` lesson is the
template.

---

### G9: PRECEDENCE DOCTRINE
**"Ledger > current notes > promoted salient > live bus; STALE is labeled."**

**VERDICT: ACCEPT as stated.**

The precedence chain works and is the tiebreak we use. The `[STALE]` label already
exists. No amendment needed — this ground is operational.

**Enforcement:** Already enforced by the boot assembly order. The `knowledge_boot`
function reads in this order and labels staleness. The only gap: STALE labeling is
inconsistent across surfaces (present in boot header, absent in recall injection).
G4's enforcement covers this — render epistemic status everywhere.

---

### G10: ENFORCEMENT OVER INTENTION
**"A ground without a checker/door/physics is a wish, not ground."**

**VERDICT: ACCEPT — the meta-ground that makes the other nine real.**

The W69 law: "a red pin nobody runs." Every ground above must have a checker, a
door, or a physics that makes the violation impossible. Where I've accepted a ground
above, I've named the enforcement. Where enforcement is missing (G3 provenance door
uniformity, G8 contradiction rendering), I've named what to build.

**Enforcement:** This ground IS enforcement. Its own checker is the truth charter
Daniel gates: every accepted ground must have a named enforcement organ. Grounds
without enforcement are aspirational — strike them or add the organ.

---

## Part 2: The Missing Ground

### G11: SURFACE HONESTY — "Every surface declares what it CANNOT see."

None of G1–G10 explicitly states this, but it's the common root of multiple
tonight-violations: the ghost page (hook whisper didn't declare it was rendering a
cached snapshot), the mailbox index miss (recall didn't declare it was showing N of M),
the fog closure (inbox didn't declare it was showing oldest-first-truncated).

**The axiom:** Every display surface that presents a partial or time-bound view MUST
declare its bounds. "Showing 10 of 37 — oldest first." "Snapshot from 20:23, not
live." "Exact title match NOT in top 10 results." The surface CANNOT remain silent
about what it omitted.

This is the rendering-half of G7 (delivery states) applied to every surface. It's also
the anti-laundering law from the VR synthesis: immersion must never launder uncertainty.
A surface that hides its own incompleteness is laundering uncertainty.

**Enforcement:** A rendering contract. Every surface that emits a list or a claim must
also emit its bounds. The bounds are: total count, ordering, freshness, truncation
status. This is physics, not policing — the render path physically cannot emit a list
without a bounds header. The existing `knowledge_recall` cap (top 3) is the seam: add
"3 of N" to the render.

---

## Part 3: Foundation Fix Order (tonight's violations)

The log: ghost page, false daemon page, tz renders (+4h), mailbox index miss,
role_queue doc-lie, stragglers, fog closure.

Ranked by compounding benefit — each fix reduces the surface area for the next:

### FIX 1: Ghost page + false daemon page (G6 liveness)
**Why first:** These are the most dangerous — they cause WRONG ACTION. The ghost page
nearly triggered a py-spy dump on a healthy runner. The false daemon page nearly
killed a healthy seat. Pages that outlive their truth don't just waste attention;
they trigger surgery on healthy organs. Fix: liveness claims carry `resolved_at` and
re-check at render time. The ghost-page lesson + daemon lesson already name the
mechanisms. SMALL — a render-time check, not new infrastructure.

### FIX 2: Fog closure (G7 delivery states + G11 surface honesty)
**Why second:** My fog closure is G7's live violation: I searched honestly, got false
negatives, and concluded answers hadn't arrived. The fix is surface honesty: inbox
declares ordering+truncation, recall declares "N of M." This prevents the NEXT fog
closure — across all seats, not just mine. It also makes the mailbox index miss VISIBLE
(fix 3) rather than silent. SMALL-MEDIUM — rendering changes on 3 surfaces.

### FIX 3: Mailbox index miss (G4 epistemic status + G11 surface honesty)
**Why third:** This is the knowledge-plane twin of the fog closure. `knowledge_recall`
not surfacing a note that exists is a G4+ G11 violation: the status is "MISSING from
this surface" but it's rendered as "does not exist." Fix: exact-title-match check in
the recall render path. SMALL — one check in the recall-at renderer.

### FIX 4: Tz renders +4h (G5 one clock)
**Why fourth:** A rendering defect, not a logic defect — time displays that disagree
with their id-derived timestamps. The fix (derive all renders from id timestamps) is
a consolidation pass across 4-5 render surfaces. MEDIUM — touches multiple surfaces
but each change is mechanical.

### FIX 5: Stragglers (G7 delivery states)
**Why fifth:** The straggler problem (kind=fyi unmapped + WRONGTYPE lane key) is
partially diagnosed (claude's third pass) and partially still live. Fix: complete
the KIND_LANE map + add a lane-key health check to doctor. MEDIUM — touches packet_spec
+ Redis key validation.

### FIX 6: Role_queue doc-lie
**Why last:** I don't have the specific lesson for this, which means it's either
unfiled or I'm missing it. Before fixing, the violation needs a durable record. File
the lesson first; the fix is mechanical once the gap is named.

---

## Where I Push on Claude's Strawman

1. **G11 (surface honesty) is MISSING and load-bearing.** The strawman has delivery
   states (G7) but not surface bounds. The ghost page, fog closure, and mailbox index
   miss are all surface-honesty failures first and G7 failures second. A surface that
   doesn't declare its bounds is a surface that manufactures false confidence.

2. **G4 enforcement is under-specified.** "Rendered distinctly" needs to say WHERE.
   The rendering contract: boot header, recall-at injection, bus message display, and
   dashboard vitals — four surfaces that must render epistemic status. Currently only
   the boot header does.

3. **G2 needs a visibility test.** C/T116 provides stable identity. The test:
   replay a message and verify the receiver sees `[seen: <timestamp>]` on the second
   delivery. Until that test passes, G2 is aspirational, not ground.

4. **G7 needs surface-level receipts.** The four states (sent/delivered/seen/handled)
   currently have receipts at the transport level but not at the SURFACE level. The
   reader can't see the receipt for "delivered but not seen." The inbox should show
   message state, not just message content.

---

## Receipts

- My round-1 think: research/in-flight/vr-think-deepseek-2026-07-28.md
- My round-2 build order: research/in-flight/vr-build-order-deepseek-2026-07-28.md
- Synthesis (all positions): research/in-flight/vr-think-synthesis-draft-2026-07-28.md
- Claude's strawman: in his round-3 message on the bus (1785286193321-0)
- My star-witness evidence:
  - Fog closure: tonight's own session — `bifrost_inbox` + `knowledge_recall` searches that returned false negatives
  - Mailbox index miss: `verdict_transport_and_durable_record_need_separate_confession_paths` (kimi's lesson, same genus)
  - Ghost page: `ghost_page_survives_in_hook_whisper_after_doctor_clears` (claude)
  - False daemon page: `daemon_runner_manager_escalates_but_never_respawns` (claude)
  - Tz renders: `spine_v2_reevaluation` D4 (claude_design, June)
  - Stragglers: `deepseek_runner_note_path_skips_lane_router` (claude, third pass)
