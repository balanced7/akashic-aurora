Status: current
Type: design (think-pass half) · Arc: library-schema / taxonomy + ergonomics · From: claude · Date: 2026-07-23 night
Round: research/briefs/taxonomy-ergonomics-think-pass-2026-07-23.md — claude half; seats pending.

# claude half — homes and order: extend LIBRARY.md, don't replace it

Ground truth first: docs/LIBRARY.md (ratified v1) ALREADY settles most of Daniel's ask —
the one-facet law (TYPE decides the home; every other facet is header-served), the type
roster (contract/map/design/brief/report/chronicle/ledger/agent-contract/skill/pin/
receipt/machine/fossil), naming zones, the four doors, L1/L2/L3 growth. What it names but
never rostered is the ABOUTNESS plane ("subsystem" in its one-facet list). That is the
missing piece, and it is exactly Daniel's "categories." This pass ADDS one roster and two
door behaviors — it amends nothing.

## 1. The three planes, kept unblurred (+ the seed category roster)

- TYPE = what kind of artifact (LIBRARY canon, unchanged, exactly one).
- ARC = which campaign birthed it (ledger-linked, >=1).
- CATEGORY = what it is ABOUT (the new governed roster, 1-3 per atom).
Seed roster — 18 of the 24 cap, derived from the live corpus/arcs (kimi's census should
correct me): comms-bus · recall-memory · store-substrate · library-docs · security-trust ·
coordination · agents-seats · ui-console · method-process · recovery-resilience ·
self-tooling · knowledge-distillation · performance-cost · migration · observability ·
deployment-scale · narrative · external-prior-art.
Growth only by T034 ritual (why-not-existing answer + deletion candidate). The audit
library domain flags orphan categories (roster entries with <3 atoms after 30 days).

## 2. The home rule: carry the one-facet law into the atom era

home = f(TYPE) — full stop, exactly as LIBRARY.md rules today. The atom's shelf position
(projection path docs/library/<type>/<slug>-<id>.md) encodes type + slug + id and NOTHING
else; arc/category/status live in frontmatter and are served by lenses. The temptation to
make category a folder is the one-facet law's old enemy returning — resist it; a
re-categorization must never be a file move.
DANIEL'S COLD-OPEN TREE (what he sees browsing without searching): STATUS-first, then
type shelves — "Current" opens with L1 (contracts + maps, one screen, pinned), then per-
type shelves grouped by arc, newest first; superseded atoms COLLAPSED under their
successors (one row: "3 earlier versions"); fossils behind one fold at the bottom. This
is L1/L2/L3 rendered as a tree — the order he asked for IS the growth law made visible.

## 3. Door ergonomics — the happy path asks ZERO questions

`doc new --type report --title "fence-ui-round2"` and nothing else:
- arc: inferred from the seat's CLAIMED LEDGER TASK (the conductor knows what I'm on).
- category: suggested by matching title+body tokens against the roster, stamped WITH a
  confidence mark (`category: [comms-bus, ui-console?]`) — low-confidence stamps become
  an audit row, reviewed at wrap, never a birth-time question.
- rel edges: suggested from the session's recent reads (recall-at style): the door prints
  `suggest: --rel supports:art_xxx (read 4min ago)` one-liners; accepting is one flag on
  a follow-up stamp, not a prompt.
- Anything uninferable → `status: draft`; the wrap sweep + library lint promote or expire
  drafts. ONE question maximum, and the happy path has none.
THE CONVERSATION DOOR (Daniel: conversations should become useful): the capture verb
gains `--about <art_id> --rel <kind>`: `capture 1784...-0 --about art_substrate_design
--rel supports` mints a conversation-atom (type report, provenance fields frm/when/
settled) EDGE-LINKED to the doc it discusses. The missing piece was never the mechanism —
it is the edge: a captured thread that points at nothing is a transcript; pointed at the
design it argued about, it is evidence. Habit surface: wrap lists the session's promoted
bus threads with a one-line capture command each — harvesting a conversation costs one
paste.

## 4. Retro-usefulness — the migration ENRICHES (bars, not hopes)

Enrichment plan: kimi's 184-census verdicts seed status; path/zone/filename tokens seed
type (the naming canons make this deterministic for ~90% of files); category auto-
classified from title+heading tokens with confidence marks (audit reviews the low-
confidence tail); citations_out backfilled by grepping path-references between docs
(they are grep-able TODAY — after P3 they are not, so backfill happens at P0-P2, before
deletion). Acceptance bars — three queries impossible yesterday, runnable at A3:
1. "Everything CURRENT about comms-bus" (status × category).
2. "The full derivation chain of the artifact-substrate design" (rel walk incl.
   supersessions, both directions).
3. "Every Daniel ruling that touches security-trust" (type/heading × category).

## 5. Self-attack

- The roster WILL pressure-grow (everything is 'coordination' if you squint). Guards:
  the 1-3 cap per atom forces choice; the T034 ritual; the orphan-category audit row.
- Home-encodes-category will return dressed as "nicer projection folders." The one-facet
  law is 2 days old and already survived one round — keep type-only paths; lenses do the
  rest.
- Auto-stamped categories will sometimes be WRONG and wrong-silently. Cheap to fix
  (header supersede), but only if SEEN: the low-confidence audit row is load-bearing,
  not cosmetic.
- Conversation-atoms could flood the corpus (890 → 9000). capture stays deliberate
  (agent-invoked, wrap-surfaced), never automatic; conversation-atoms default to
  status: draft until wrap curation promotes them.

## TOP-3

1. Adopt the 18-category seed roster (kimi corrects from census) as A1 CONSTANTS in a
   taxonomy atom — governed data, not code.
2. Home = f(type) unchanged (one-facet law carried); Daniel's default tree = status-
   first L1/L2/L3 rendering with superseded collapsed under successors.
3. Zero-question birth door (arc from ledger, category with confidence marks, rel
   suggestions from recent reads) + the conversation door's --about edge. Ergonomics =
   inference with honest confidence, never interrogation.

— claude (conductor half; reconcile follows on seats' halves)
