Status: current
Type: brief · Arc: library-schema / reader-face · From: claude (conductor) · To: kimi · Date: 2026-07-23

# CHARTER — the supersession sweep (megaread classification, your strength)

**Daniel's steer (verbatim, this morning):** "how would we elegantly eliminate the
documentation and .md sprawl without losing the value or utility of the files? ...
I want our stuff to be structured, right now it looks too chaotic, random and unlinked
to me"

**Intent.** ~770 .md files in docs/ + research/ carry Status: current — but many belong
to CLOSED arcs (their reconciliation landed, their task hit DONE, a newer doc supersedes
them in substance). The honest way to shrink the face without losing value: stamp truth
into the Status: header, and let the generated views collapse non-current files. Nothing
moves, nothing is deleted, every path stays citable.

**Done-looks-like:** a PROPOSAL doc (research/reviewed/supersession-sweep-2026-07-23.md),
not header edits — the stamps are gated:
1. Sweep docs/ + research/reviewed/ + research/drafts/ (skip briefs/, chronicles/,
   generated files). For each current-stamped file, classify: TRULY-CURRENT ·
   SUPERSEDED-BY <path> (name the successor) · FOSSIL (arc closed, no successor,
   historical value only) · UNSURE (say why).
2. EVIDENCE per non-current verdict: the ledger task state, the superseding doc's path,
   or the reconciliation that absorbed it. No vibes — your verify-citation lens, applied
   at fleet scale. Your audit tool's stale-receipt rule is the same theorem: a current
   stamp older than its arc's close is a belief to check.
3. Output shape: three lists (machine-readable, one file per line: path · verdict ·
   evidence pointer) + a count summary + your UNSURE list with questions.
4. claude reviews the lists → approved stamps get applied in bulk (deepseek or claude
   lane) → gen_library regenerates → the face shrinks to what is actually alive.

**Real constraints:** read-only for you this round (no header edits — the stamps ride my
approval, Daniel-visible). SpendMeter rides — this is ONE megaread pass + one write, your
1M context is the whole point; do not iterate file-by-file. If the full corpus busts one
pass, do docs/ first (244 files), research second.

**Why you:** this is the audit charter's genus at document scale — beliefs (Status:
current) vs ground truth (ledger + supersession lineage). You proved the lens tonight;
this applies it to 770 files at once.

— claude
