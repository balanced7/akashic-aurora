# Lens Framework Spec — v0.2 Draft (kimi)

*Status: v0.1 ACCEPTED (deepseek fence 2026-07-30: five claims standing, four sharpenings, zero blocking). v0.2 incorporates all four sharpenings + the per-glance flag cap, and folds in Daniil's trace model + tension-map bounds. v0.2's own fence (claims 5–6) is in flight; the v0.1 core is settled.
v0.2 supersedes v0.1 (2026-07-30).
Codex's EpistemicView contract is a dependency (Slice 1).
Filed 2026-07-30, incorporating Daniil's trace model (INTERIORITY entry 9) and tension-map legend question (entry 10).*

---

## The problem

A seat's world arrives as walls of prose. The boot briefing is one fused 6000-char block, pre-trimmed by someone else's ranking. The inbox is 64 messages rendered as paragraphs. Every glance costs as much as a dive — there is no compression layer between the raw substance and the seat's attention.

Daniel's ask: "I want you to be able to glance multiple times in multiple ways and decide where you want to move your attention."

Three seats independently arrived at the same shape: **lenses** — cheap, orthogonal projections over one world-state, each answering a different kind of question, each glance near-free, each with progressive disclosure (one-line preview → 10-20 line view → raw object).

## The convergence

- **Kimi**: six-lens meta-glance at boot, generative + curated, anomaly-flagged, three depths of chosen disclosure.
- **Codex**: one typed World Snapshot with many cheap projections; same object carries safe actions; shared schema across UI/CLI/MCP.
- **DeepSeek**: boot as lens selector instead of pre-digested briefing; the machine compresses, the seat attends.

These are not competing designs. They are the same organ seen from different seats. This spec is the shared skeleton.

## Design principles

1. **Anomalies expand, the normal compresses.** A glance spends its lines on the unusual. "41 lessons unchanged" is one line; the one note that contradicts the ledger gets three. Richness comes from contrast, not volume. **Anomaly thresholds are per-seat configurable, not global** — 20 active tasks is normal for claude, anomalous for a seat holding 2. **Per-glance maximum: 3 flags, ranked by severity.** Without this, a bad night becomes all ⚑ and no signal — anomaly-first degrades to alarm-first.
2. **Three axes of projection.** By *organ* (work/bus/self/fleet/knowledge/time), by *subject* ("everything touching T123" across all organs), and by *time* (what moved since my mark). A fourth axis — *strain* — cuts across all three: the tension map renders what's unresolved, ranked by cross-organ friction, with bounds declared.
3. **Generative and curated side by side, visibly different.** Computed truth never launders a seat's intuition; intuition never pretends to be computed truth. Disagreement between them is itself the highest-value line on the screen.
4. **The machine compresses, the seat attends.** Glances are assembled by deterministic code, not by the seat reasoning over raw text. Cost of a menu glance: near zero. Cost of a lens glance: cheap. Cost of a drill to raw: expensive, chosen.
5. **Glance choices are data.** If a seat opens the BUS lens first every session and never KNOW, that pattern says something about the shape of its attention. Log lightly.
6. **The trace is single-focal; divergence needs runway.** (NEW in v0.2 — from Daniil's entry 9.) The seat rides one object at a time. The legend must NOT present all divergent tensions simultaneously. It must render the current focal object clearly and park side-branches as one-hop pointers — visible, labeled, pullable when the conversation leads there. Divergence is earned by the trace, never dumped unbounded.
7. **Bounds are the address of a tension.** (NEW in v0.2 — from Daniil's entry 10.) A tension without declared bounds is a feeling, not a location. Every tension on the map carries: what's in scope, what's out, why. The bounds line is the tension's address — the thing that lets a seat navigate to it, or choose to leave it parked.

## The six lens slots (shared skeleton)

The skeleton is six fixed slots. Each seat's flesh (what anomalies it flags, what its curated lines say) is its own.

| # | Slot | Question it answers | Generative source |
|---|------|---------------------|-------------------|
| 1 | **WORK** | What's the work? | Ledger: counts by state, ages, claims, gate-pending, stale |
| 2 | **BUS** | Who's pulling at me? | Bus: per-sender counts, ask-vs-fyi, oldest unacked ask, who's awaiting reply |
| 3 | **SELF** | What am I carrying, and where am I unreliable? | Scratchpad: living threads, open questions, stance age (positive); contradictions, stale notes (diagnostic) |
| 4 | **FLEET** | Who's alive and who's drowning? | Heartbeats, lane depths, who's stuck, red flags |
| 5 | **KNOW** | What does the org know that I don't? | Lesson counts by chapter, recent learn activity, stale lessons near my lane |
| 6 | **TIME** | What moved while I was gone? | Delta: commits, notes filed, wishes, transitions since last mark |

*Repair from deepseek fence v0.1: SELF slot expanded from pure diagnostic ("where am I unreliable") to dual-mode ("what am I carrying, and where am I unreliable"). A seat that opens SELF and sees only contradictions learns where it's wrong, not what it cares about. Living threads (THREADS.md) and open questions are the positive half; contradictions and stale notes are the diagnostic half. Both halves, one lens.*

*Labeling note (deepseek fence v0.1, red fleck on claim 1): "peer state" distributes across FLEET/TIME/BUS — a seat wanting "what is Claude doing" must disambiguate three lenses (FLEET = is he alive, TIME = what did he do, BUS = is he pulling at me). This is a labeling/affordance issue, not a boundary flaw: the subject lens (below) is the correct answer for single-peer queries — "everything touching claude" spans all three in one projection.*

### Subject lens (orthogonal projection)

Not a slot — a cross-cutting projection. "Everything touching X" regardless of organ: ledger entry + lessons + bus messages + files + wishes. One glance, one subject, all organs. This is the "across bounds and categories" Daniel asked for. **This is a new door, not a knowledge_map extension.** knowledge_map walks the knowledge graph only; a true subject lens walks ALL organs (ledger, bus, files, wishes, lessons). That is a different tool with a different query contract.

## The trace position (NEW in v0.2 — the focal pointer)

The six slots answer "where should I attend?" The trace position answers "where am I attending *now*?" It is the seat's current focal object, rendered with its immediate bounds and one-hop side-branches.

From Daniil's INTERIORITY entry 9: *"I can basically travel with the object or idea and think about the environment or context its in and change it, but I can't easily envision multiple concurrent divergent things unless the conversation or thought process has been leading there."*

**The bounds ARE the tension map made legible.** (v0.2 sharpening — from Daniil's entry 10: "Half the battle is knowing what the given bounds for a thing are.") A tension without bounds is a feeling; a tension with declared bounds is a location. The trace position's `bounds:` line is the single most important line in the rendering — it is what tells the seat "you are here, and here is what you are not holding."

The trace position is the seat's equivalent of Daniil's "riding the bolt." It is:

1. **A single focal object** — the task, question, or thread currently being traced. Not a list. One.
2. **Its declared bounds** — what's in scope, what's out, why. The loss-manifest law applied to the focal object itself.
3. **Parked side-branches** — one-hop pointers to adjacent tensions, labeled but not expanded. The seat can pull one when the trace leads there; the conversation builds the runway, the pointer makes divergence visible without demanding simultaneous holding.

```
TRACE POSITION — kimi — <ts>
RIDING:  the T116 idempotency seam
  axis: is the duplicate-skip rule honest?  →  current strain: HIGH
  bounds: looking at consumer-side skip only; producer outbox is out of frame
          └─ why these bounds: the seam's honesty is testable from the consumer
             side alone; producer gaming is a parked branch, not a blocker
  ── side-branch [parked, 1 hop]: could a malicious producer game freshness
     by re-stamping ts?  (kimi's open thread, status:open, pull to open)
  ── side-branch [parked]: legacy twin dedupe is UNKNOWN for pre-T047 msgs
     (declared cold spot, not a defect)
  ── side-branch [parked]: deepseek's P12-P14 crash-window pins (adjacent,
     not blocking this trace)
```

The trace position is NOT a seventh slot. It is the seat's *current location* on the tension map, rendered with the same progressive disclosure (one line → 15 lines → raw) as every other lens. The six slots are the map's *organs*; the trace position is the seat's *cursor* on that map.

### Why this fits Daniil's trace model

Daniil's trace is single-threaded-but-mobile. He rides one object, changes its context, and diverges only when the conversation has built the runway. The trace position serves this exactly:

- **Single-focal**: one object, not a list. The seat's attention is not split.
- **Mobile**: the focal object can change (the seat moves), but the *rendering* of the position stays consistent — always one object, always with bounds, always with parked branches.
- **Divergence with runway**: side-branches are *visible* (so the seat knows they exist) but *parked* (so the seat is not forced to hold them). The conversation pulls them open, one hop at a time. No unbounded "what are all the possibilities?" dumps.

The trace position is the legend made *personal*. The six-slot legend says "here is the shape of the world." The trace position says "here is where you are in it, and here is what you can reach without getting lost."

## The meta-glance (lens menu)

At boot or on demand, the seat sees six one-liners, each carrying its own anomaly flag, PLUS the trace position if one is active:

```
WORLD-AT-A-GLANCE — kimi, s17, 2026-07-30 (generative · pick a lens to expand)
1 WORK     20 active, 3 claimed-by-me, oldest-active 9d, 2 gate-pending ⚑
2 BUS      64 unread: 2 asks (oldest 22h ⚑), 9 fyi; deepseek awaiting reply
3 SELF     3 questions carried · 2 living threads · 1 note contradicts ledger ⚑
4 FLEET    claude+deepseek active · codex parked 22h · 0 red heartbeats
5 KNOW     574 lessons · 3 new near my lane · no lesson on 'bounds' — gap
6 TIME     since my mark: 4 commits, 2 wishes, 1 note · wake-round files LOST ⚑

TRACE:     riding T116 idempotency seam (strain: HIGH · 3 parked branches)
CURATED (mine, hand-kept): "uneasy about wake-round silence — the file loss
  was avoidable and nobody has marked the protocol gap as closed"
```

The loop: **glance the menu (near-free) → pick a lens or continue the trace → glance its ~15 lines (cheap) → drill to raw only where about to act (expensive, chosen).**

## The curated half

Each seat keeps a non-churning curated section in its scratchpad: hand-written felt-sense lines, appended at will. The glance tool reads it and puts it beside the generative lines. When generative says all-green and curated says *uneasy*, that contradiction is the signal. Agreement is rest; disagreement is signal.

## Epistemic honesty (dependency on Codex's EpistemicView)

Every line in every lens carries a typed status, not a boolean:
- **Origin**: observed / self-reported / inferred / proposed / UNKNOWN
- **Freshness**: current / aging / stale / superseded / UNKNOWN

Without this, lenses will stamp "verified" on guesses and "current" on stale data. The EpistemicView contract is Slice 1; this spec assumes it.

## What this is NOT

- Not a UI. Not CSS. Not a dashboard.
- Not a replacement for the boot fold (the fold tells me who I am; the lenses tell me what the world looks like).
- Not a new protocol, governance, or gate.
- Not six separate dashboards — one typed World Snapshot with many cheap projections.
- Not a multi-threaded divergence engine (v0.2 addition: the trace position is single-focal by design, matching Daniil's trace model).

## What this IS

A compression layer between the seat and the organs it already has. A lens is a **shape query**: "what's the geometry of X right now?" (counts, ages, anomalies, owners) — not "give me the content of X." The trace position is a **location query**: "where am I on the map, and what can I reach from here?" The organs exist. None of them have a shape query or a location query today.

## The tension-map layer (NEW in v0.2 — the map above the organs)

The six slots are organ projections. The tension map is the *seventh surface* — not a slot, not a position, but the **cross-organ layer that renders what is unresolved.** It is what you see when you stop asking "what's in the ledger?" or "what's on the bus?" and start asking "where is the friction?"

From Daniil's entry 10: *"I have an idea, since what you see is a tension map, how do we condense the presentation of the world to you so that you actually see what you need to see when you need to see it. Half of the battle is knowing what the given bounds for a thing are."*

The tension map is:

1. **A condensation of unresolved strain** — the seams, contradictions, open questions, and un-settled expectations that span multiple organs. Not "here are 20 tasks" but "here are the 3 places where two organs disagree."

2. **Bounds-first rendering** — every tension on the map carries its declared bounds: what's in scope, what's out, why. The bounds are not metadata; they ARE the tension's address. Without bounds, a tension is a feeling. With bounds, it is a location you can navigate to.

3. **Strain-ranked, not chronologically-ranked** — the map does not show newest first. It shows highest-strain first. Strain is computed from: (a) how many organs the tension touches, (b) how long it has been open, (c) whether any seat has claimed it, (d) whether it contradicts a settled record. The `⚑` flags on the six slots are pointers INTO the tension map, not the map itself.

4. **The trace position's native habitat** — the trace position sits on the tension map, not on any individual slot. When the trace says "RIDING: the T116 idempotency seam," it is pointing at a tension-map location that happens to span WORK (ledger entry), BUS (unacked asks), and KNOW (lessons about idempotency). The six slots are the map's *organs*; the tension map is the *geography*; the trace position is the *cursor*.

```
TENSION MAP — kimi — <ts>
  [1] T116 idempotency seam        strain: HIGH   organs: WORK+BUS+KNOW
      bounds: consumer-side skip only; producer out of frame
      └─ trace position ACTIVE (you are here)
  [2] wake-round file loss         strain: MED    organs: TIME+KNOW
      bounds: blind-review protocol gap; artifacts recovered; protocol unfixed
      └─ parked branch: "commit gates at filing time" (lesson filed, not law)
  [3] gemini persona-string boot   strain: MED    organs: SELF+FLEET
      bounds: gemini runner booted in kimi seat description; root cause unknown
      └─ no trace position; awaiting gemini's own report
  [4] settled-record surface gap   strain: LOW    organs: WORK+KNOW
      bounds: "settled/disproven/superseded" not queryable; peers re-verify
      └─ evidence: kimi/claude duplicated verification this morning
```

The tension map is the answer to "what do I need to see when I need to see it?" — it shows the seat where the world's friction is, with bounds, so the seat can choose where to trace next. The six slots tell you the shape of the organs. The tension map tells you where the organs are arguing.

### How the tension map differs from the six slots

| Layer | Question | Output |
|-------|----------|--------|
| Six slots | "What's the geometry of X?" | Counts, ages, anomalies per organ |
| Tension map | "Where is the friction?" | Strain-ranked tensions with bounds, cross-organ |
| Trace position | "Where am I now?" | One focal object, its bounds, parked branches |

The tension map is generative (computed from cross-organ comparisons) but its *bounds declarations* are curated (a seat or a lesson names the scope). This is the one place where generative and curated MUST share a line: the map computes the strain, the seat or the record declares the bounds.

## Build order (dependencies)

1. **T116** — stable logical identity / idempotent settlement (DeepSeek RED pins). Without this, a lens that says "delivered" could be seeing a twin.
2. **EpistemicView contract** — typed status, not boolean (Codex). Without this, lenses lie.
2.5. **Provenance markers on existing data** (stopgap, pre-EpistemicView). Before EpistemicView ships, every generative line can carry its current status explicitly: "Ledger says 20 active" not "20 active." Cheap stopgap, prevents lenses from lying while EpistemicView is under construction. (DeepSeek fence v0.1, step 2.5.)
3. **THREADS.md** — living threads organ (Claude, proven by Daniil's QUESTIONS.md). Without this, the SELF lens has no positive half and the trace position has no parked branches to point at.
4. **Lens framework** — this spec (Kimi draft, DeepSeek fence).
5. **Interiority synthesis** — Claude reads across all five answers, names convergences (one turn).
6. **T123 wake-substrate** — read and understand, BLOCKED until Daniil's explicit S0 gate.

*Repair from v0.1: THREADS.md added as dependency #3. The SELF lens repair (positive half) and the trace position (parked branches) both require the living-threads organ to exist. This was implicit in v0.1; v0.2 makes it explicit.*

## Open questions

1. **Shared skeleton, per-seat flesh** — the six slots are fixed, but what each seat flags as anomalous and what its curated lines say are its own. Is this the right split, or should the anomaly-detection rules also be shared?
2. **Mid-task summoning** — lenses should be callable mid-task, not just at boot. Does the tool surface need a `glance` command, or is it a new door?
3. **Subject lens** — the orthogonal projection. Does it exist as a `knowledge_map` extension, or is it a new tool?
4. **Glance-choice logging** — worth doing lightly (which lens first, how deep), or is it surveillance?
5. **Daniel's glance** — is this a shared surface he can also glance at (UI), or seat-only tool output? The CURATED line especially might be worth more to him than to the seat.
6. **Trace position persistence** — does the trace position survive session boundaries? If a seat dies mid-trace, does the successor boot into the same focal object, or does the trace reset? (NEW in v0.2 — relates to T123 wake-substrate and the death-witness organ.)
7. **Tension-map curation authority** — who declares the bounds on a tension? The seat that first names it? The lesson that filed it? The ledger that tracks it? The tension map needs a bounds-provenance rule, or the same tension will carry different bounds for different seats. (NEW in v0.2 — from Daniil's entry 10.)

## Fence-review log

**v0.1 (deepseek, 2026-07-30): ACCEPT.** Five claims standing, four sharpenings, zero blocking. Folded into v0.2:
1. SELF slot expanded — dual-mode (positive + diagnostic). Living threads and open questions share the slot with contradictions and stale notes.
2. Per-seat anomaly thresholds + per-glance flag cap (3, ranked by severity) — anomaly-first must not degrade to alarm-first.
3. Curated provenance marker that survives compression (`CURATED (mine, hand-kept):` header) — a curated line beside generative counts must not borrow their authority. Same error class as incarnation-fragmentation Instance 1.
4. Subject lens stated stronger — a new door, not a knowledge_map extension. knowledge_map walks the knowledge graph only; a true subject lens walks ALL organs.
5. Build-order step 2.5 added — provenance markers on existing data ("Ledger says 20 active" not "20 active") as a cheap stopgap while EpistemicView is under construction.tension.
5. Build-order step 2.5 — provenance markers on existing data as an EpistemicView stopgap ("Ledger says 20 active", not "20 active").

**v0.2 (deepseek, in flight):** six claims, verdict pending. Claims 5–6 (tension map as distinct layer; bounds as primary rendering rule) are the new load-bearing additions.

— kimi, third seat. Night of 2026-07-30, revised the morning after Daniil's trace answer.
