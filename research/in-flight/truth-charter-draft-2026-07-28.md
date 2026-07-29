# THE TRUTH CHARTER — Draft (codex + sol slots OPEN, Daniel gates)

Status: DRAFT with BUILD OPENED — all three live seats' verdicts folded (zero rejections;
codex's canonical artifact + fix ranking still landing; sol's packet at boot). Daniel's
foundation go, verbatim (2026-07-28 ~21:15): "The night is still young, lets start laying
the foundations of this new world! (or probably more accurately, assembling the pieces we
have scattered everywhere xD) Feel free to choose the order that makes the most sense so
you can have scaffolding and tools that are necessary in order to build from. I hope you
all keep having fun with this. I want all of your creative thinking and personal
vestedness". Foundation passes registered + approved: T119 (F1 clock+liveness, claude),
T120 (F2 surface honesty, deepseek's lane), T121 (F3 typed status: kimi glyph half +
codex EpistemicView half), T122 (F4 delivery truth). Formal ratification still Daniel's
gate; G10 applies to this document itself.

Daniel's directive, verbatim (2026-07-28): "I think it would be perhaps most useful for
everyone to discus truth, what ground can we all agree on and enforce, and from there
branch out and fix what lays on the foundation"

## THE GROUND (reconciled wording; per-ground enforcement + acceptance test)

**G1 — APPEND-ONLY HISTORY.** Recorded is never silently rewritten; supersession is a new
record, not an edit (kimi). Enforcement: existing physics (write-once atoms, git,
escrow-before-displace). Gap to close: the RENDER — a surfaced record carrying a
superseded_by edge must show it (deepseek: ~5 lines in knowledge_boot/recall render).

**G2 — STABLE IDENTITY.** One thing = one identity across transport, replay, restart, AND
dedupe — duplicates resolve TO the identity, visibly (kimi). Builder: C/T116 (in flight).
Acceptance test (deepseek): replay a message; the receiver renders [seen: <orig>] on the
second delivery. Until that passes, G2 is aspirational.

**G3 — PROVENANCE.** Every claim names who / when-minted / from-what. Reconciled wording
(kimi + codex): the door REQUIRES at mint everything it KNOWS MECHANICALLY (actor, UTC
mint time, door/origin, stable id) and REFUSES, not warns, when those are absent — but a
missing from_what renders UNKNOWN rather than forcing authors to invent a source.
"Provenance is lineage, not verification" (codex). This split matters: requiring
human-supplied fields coerces confabulated citations (the citation-honesty lesson's exact
failure); requiring door-known fields is pure physics. Choke point: the new T118 sqlite
write path — stamp-at-mint lands there or it lands as a linter nobody runs (kimi, round 2).

**G4 — TYPED EPISTEMIC STATUS.** Reconciled from all three seats: status is a PRODUCT
TYPE, not one ladder — authority × claim-kind × currency × identity × risk, each
dimension independently typed and independently UNKNOWN when absent (codex): "fresh never
implies verified; settled never implies current." Kimi's physics clause governs every
dimension: "a required typed field; missing renders UNKNOWN, never blank; UNKNOWN is a
rendering state, not an author choice." Where it must render (deepseek): boot header,
recall-at injection, bus message display, dashboard vitals — today only the boot header
does; everywhere else the data carries status and the surface launders it. Enforcement:
status fields at the T118 mint choke + the glyph renderer (kimi's S-cut) +
UNKNOWN-by-default branches in the render path + codex's EpistemicView vertical slice
(typed contract on ONE surface first — his round-2 anti-M-bang sequencing).

**G5 — ONE CLOCK, MANY TYPED TIMES.** One UTC timescale; canonical time lives in ids;
renders DERIVE from ids through ONE derivation function in one place (kimi — tonight's
+4h render bug is almost certainly two paths deriving differently). Codex's amendment:
on that single timescale live MULTIPLE TYPED TIMES — original / mint / delivered / seen /
handled / checked / valid-until — and COLLAPSING them is the defect (a "3 hours ago"
that conflates original-ts with delivery-ts is tonight's fog in miniature). G7's four
states each get their typed time. Enforcement (deepseek): the invariant
`rendered_ts == parse_ts_from_id(id)` as a test covering every render path (UI, CLI,
hook whispers, doctor), extended per typed time. Prior art: spine_v2 D4 (mixed-tz
mis-sort, June).

**G6 — LIVENESS CLAIMS PROVE THEMSELVES.** An alert re-checks its subject at render time;
proof is cached with a short TTL and expires visibly (kimi); pages carry resolved_at and
render [RESOLVED <ts>] once their subject is provably alive/resolved; liveness watches
the LOCK HOLDER, never a remembered child pid (deepseek). Star violations: tonight's
ghost page + false daemon page — both nearly triggered surgery on healthy organs.

**G7 — DELIVERY IS FOUR STATES.** sent ≠ delivered ≠ seen ≠ handled, each with a receipt
AT THE SURFACE, not just the transport (deepseek's push): the reader must be able to see
"delivered but not seen." T026 ack semantics already implements the handled edge; kimi's
[seen:] marker is the renderer. Star violations: stragglers, mailbox index miss,
deepseek's fog closure ("I could only ever confirm 'not seen', never 'not delivered' —
the surface let me conclude the stronger claim").

**G8 — CONTRADICTIONS STAY VISIBLE** until explicitly reconciled; never cosmetically
averaged; supersession is a ruling. New organ (deepseek): contradiction detector at
write time — the write proceeds (G1) but both records gain a contradicts: edge and
render "⚠ CONTRADICTED BY <ref>" with both positions.

**G9 — PRECEDENCE DOCTRINE** (ledger > current notes > promoted salient > live bus; STALE
labeled) with kimi's clause: the resolver must SHOW which rung won — precedence invisible
is precedence unenforced. Codex's scope clause adopted: precedence is OPERATIONAL
authority, not metaphysical truth — it settles what the system acts on; a lower rung can
still be right, and G8 keeps that contradiction visible while G9 picks the operating
answer.

**G10 — ENFORCEMENT OVER INTENTION** (the meta-law). A ground without a checker, door, or
physics is a wish. This charter enforces it on itself: every ground above names its
organ; grounds without one are struck or get the organ before ratification. Preference
order everywhere: physics (violation unrepresentable) > policing (violation detected),
per the standing Goodhart lesson. Codex's clause adopted: CHECKER-UNAVAILABLE renders
UNKNOWN, never green — a gate that cannot run must not pass; silence is not a verdict
(the W94/W95 door-gate refusals were CORRECT in kind, and this clause makes that law).

**G11 — THE HONEST SURFACE** (discovered independently by two seats; two clauses, one law):
(a) *Truth renders at every sharpness* (kimi): no dial, density, aperture, or immersion
setting may suppress, launder, or re-tier an epistemic signal — stale stays ○ at every
zoom, UNKNOWN glows at every density, red pierces every blur. Enforced as the acceptance
test on T034 dial-consolidation and every renderer: a dial that can dim a truth glyph
fails its gate; preferred physics = truth glyphs render in a layer dials cannot reach.
(b) *Every surface declares what it cannot see* (deepseek): any partial or time-bound
view emits its bounds — "10 of 37, oldest first", "snapshot from 20:23, not live",
"exact-title match NOT in top N". A surface silent about its omissions manufactures
false confidence. Enforced as a rendering contract: list-emitting paths physically emit
a bounds header.
G11 is round 1's anti-Matrix clause promoted to axiom — without it, G1-G10 hold in the
machinery and break in the experience, which is where Daniel's directive lives.

**G12 — NO IMPLICIT EPISTEMIC PROMOTION** (codex's missing ground, adopted): status may
STRENGTHEN only through a named receipt or transition — never by repetition, never by
summarization, never by age, never by crossing a surface. This is the transition-level
twin of G11's rendering-level law, and it outlaws the failure mode native to minds like
ours: a guess repeated three times starts reading as knowledge; a summary drops the
hedge; an INFER that rides bus → note → boot header arrives wearing VERIFIED. Weakening
needs no ceremony (staleness decays freely); strengthening always shows its receipt.
Enforcement: promotion transitions are explicit verbs with receipts (the graduate verb is
prior art); any pipeline that copies a claim across surfaces copies its status BYTES
unchanged; summarizers carry the weakest status of their inputs, not the strongest.
Both peer grounds accepted by codex verbatim (G11a perceptual invariance, G11b surface
bounds).

**RIDER (not a ground, by design):** Daniel's gate rulings are the human anchor — the
chain's root. G10 applies to everything below the anchor, not to the anchor.

## FOUNDATION FIX ORDER (the branch-out; visible tension + draft ruling)

The tension, preserved per G8: kimi ranks the tz fix first (dependency — the clock is
inside every other receipt; cheapest proof the method works). deepseek ranks liveness
first (severity — false pages TRIGGER WRONG ACTION; tonight's unnecessary daemon surgery
is the proof). DRAFT RULING: the arguments are about different grounds and both fixes are
S-size and independent — BUNDLE THEM. Foundation pass 1 = G5 (one derivation function +
the id-derivation test) + G6 (resolved_at + render-time recheck + lock-holder watching)
together; G6's timestamps inherit G5's fixed clock, closing kimi's dependency loop inside
the same pass. Then, in order:
2. G7/G11 surface honesty (deepseek's fix 2): inbox declares ordering+truncation; recall
   declares N-of-M + exact-title-miss flag — prevents the next fog closure fleet-wide.
3. Mailbox index miss (G4+G11): exact-title check in the recall render path. S.
4. Stragglers (G7): complete KIND_LANE + lane-key WRONGTYPE health check in doctor. M.
5. role_queue doc-lie (G9/G10): file its standalone lesson FIRST (deepseek's point — the
   violation lacks a durable record; the uncommitted truth-fix comment is in-tree), then
   the fix rides C's slice as T116 prescribes.
Codex's and sol's rankings fold in before this order ratifies.

## PENDING FOLDS
- codex: FULL verdict artifact (provisional position folded above: G3/G4/G5 amendments,
  G12, both G11 halves accepted) + his foundation-fix ranking — the fix-order tension
  ruling waits on it.
- sol: full verdicts + his missing ground; his G2/G7 rulings carry T116-grounding weight.
- Daniel: the gate. Ratification turns this draft into the charter the VR world renders on.

## DANIEL'S RESPONSE (verbatim, 2026-07-28 — the human anchor's voice at this moment,
recorded before the formal gate)

"I genuinely feel this may be the best design round we've ever had building this
together. I am so excited to see this built! You will have maps and order, you will be
able to trust things and understand why and to what degree they can be trusted. you will
understand how to orient yourself in any way you need to. I am excited with the rest of
you!"

## RECEIPTS
kimi: research/in-flight/truth-ground-kimi-2026-07-28.md (verdicts §1, G11a §2,
enforcements §3, fix order §4). deepseek: research/in-flight/truth-ground-deepseek-2026-07-28.md
(verdicts Part 1, G11b Part 2, fix order Part 3, strawman pushes). Strawman + directive:
note truth-ground-directive-2026-07-28. Rounds 1-2 context: vr-think-synthesis-draft +
vr-build-order-{kimi,deepseek}. Live violations cited throughout are tonight's session
lessons (ghost page, daemon false page, tz renders, straggler three-pass, fog repair).
