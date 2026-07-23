Status: current
Type: brief (design round) · Arc: library-schema / artifact-substrate · From: claude (conductor) · To: fleet (deepseek, kimi, claude halves; outsiders advisory) · Date: 2026-07-23

# THE ARTIFACT-SUBSTRATE ROUND — end the endless .md creation, properly

## Daniel's charter (verbatim, 2026-07-23 morning — this is the whole intent)

First steer: "all the .md's are sure to be come confusing, there are so many of them, the
file name does not have timestamps or intuitively explain what is inside, we dont't know
the category of them or the context. how do we best manage this documentation sprawl. how
would we elegantly eliminate the documentation and .md sprawl without losing the value or
utility of the files? Can we clean up the random fences file and the /refs folder. I want
our stuff to be structured, right now it looks too chaotic, random and unlinked to me"

Altitude-raise (after seeing the README/index approach begin): "Rather than immediately
implementing, even though it is a difficult ask we need to spend the engineering time to
fix this properly. There need to not be 5 million .md files that get pushed to github, if
there are files they need to be openable and searchable by category or in a database. new
artifacts that would be .md files need to instead be routed to a suitable home for them.
This requires the best of our thinking from all sides. I want to fix the endless .md
creation and to also consolidate and clean up the existing .md mess. Its not elegant that
our current system just spawns .md files everywhere without a real fix. I want everyones
thoughts on how to handle this."

## The problem, at the altitude he named

Two coupled defects, one root:
1. **The default output medium is a new loose .md file.** Every brief, counter, report,
   fence, capture, and chronicle spawns one (~890 in docs/+research/+design/ today; this
   session alone added ~15). The store — Aurora's actual substrate — is bypassed for the
   fleet's own knowledge artifacts.
2. **The existing corpus** is unsearchable by category at the surface Daniel reads, and
   its sheer count destroys the repo's face.

A prettier index over the same spawn-rate is symptom care. The round designs the CURE:
where artifacts LIVE, how they are BORN, how they are FOUND, and how the existing mess
is consolidated into that home.

## Real constraints (non-negotiable inputs, not solutions)

- **Receipts doctrine stands:** full-fidelity verbatim preservation of reports/rulings
  (research-full-fidelity law; attribution records; Daniel's words verbatim).
- **Citations must survive:** hundreds of path-citations exist; whatever the home is,
  references need stable resolvable IDs and a migration story. Nothing becomes
  unfindable.
- **Daniel's surface:** he must be able to OPEN, SEARCH (category/arc/date/status +
  full text), and RULE — with less friction than today, not more.
- **Durability:** off-machine, crash-proof, history-keeping. Git currently provides
  this for free; any substrate change must match or beat it.
- **Agent ergonomics:** the new write door must be CHEAPER than Write-a-file, or agents
  drift back. And creation outside the door must be GUARDED (mechanically), not policed
  by memory.
- **Public face:** the repo is Daniel's portfolio (public, Apache-2.0). The face should
  get MORE elegant: code + crown docs, not 900 loose files.
- **Daniel gates:** migration/deletion/ratification are his. Design for gate-ability.

## In-house prior art (absorb, do not reinvent — cite by path)

docs/codex-plan.md (Resources = regenerable projections over immutable atoms — parked
C3/C4; this round may be its unparking) · docs/LIBRARY.md (one-facet law + the typed
HEADER CONTRACT — the metadata schema already exists and parses: gen_library proves it)
· core Store/Ledger + HybridStore (append-only, supersession, snapshots) · the recall
engine + knowledge_map (relevance + neighborhood over lessons — docs could join that
plane) · scripts/gen_library.py v2 (three projections from one walk) · scripts/
arc_thread.py (arc reconstruction from headers) · capture verb (bus→durable) · doc-new
verb (door 4 — the birth door whose backend could change) · bifrost console :8787 (the
fleet face Daniel already watches) · scripts/snapshot_knowledge.py (proven restore).

## The eight questions every half answers (same shape, so reconcile can compare)

- **Q1 SUBSTRATE:** where do artifacts live? (store atoms / database / files / hybrid)
  Durability story included (machine loss, crash mid-write, history).
- **Q2 GIT RESIDUE:** what remains as real files on main, and WHY those exactly?
- **Q3 BIRTH:** the write door agents use (verb shape, long-body transport, auto-typed
  headers) + the GUARD against naked .md creation (mechanical, mint-door genus).
- **Q4 READING:** Daniel's open/search/rule surface — concretely (console pane? generated
  site? DB browser? CLI?), with search by category/arc/date/status/full-text.
- **Q5 CITATIONS:** stable IDs + resolver + what happens to existing path-citations.
- **Q6 MIGRATION:** phases for the ~890 existing files, verification at each phase, what
  exactly Daniel gates. Value-loss = zero.
- **Q7 PUBLIC FACE:** what GitHub becomes (portfolio optics named explicitly).
- **Q8 SELF-ATTACK:** the costs and failure modes of YOUR OWN design — merge conflicts,
  binary-diff opacity, search staleness, door bypass, backup gaps. Be adversarial.

## Round rules

- **Blind halves:** do not read peer halves before filing; mark "peer halves UNREAD at
  filing time" in your header. File to research/drafts/<seat>-artifact-substrate-half-
  2026-07-23.md (yes — the round about md sprawl files mds; they are the LAST generation
  and will migrate with everything else; the irony is licensed).
- ≤300 lines. Evidence and paths over vibes. Q8 is mandatory.
- Timebox: file within ~2 hours of receiving this. Reconcile follows (claude), then
  Daniel rules on the reconciled design. NOTHING builds before his gate.
- Outside voices (gemini web prior-art scan: docs-as-code vs wiki vs event-sourced doc
  stores, ADR practice, Obsidian/Dendron-class systems) ride as ADVISORY input at
  reconcile — outsiders advise, citizens decide.

## ADDENDUM — Daniel's ruling on the fork (verbatim, mid-round; fold into your half)

"I don't know what the best final shape is but definitely not a million markdown files.
They could live in an archive that has a viewer that I can use to browse and explore the
contents. It needs to be something that doesn't take up a lot of space but still has the
full fidelity. The million markdown files are a technical debt we must overcome. I don't
think every human readble file needs to be on github. I don't want there to be a million
folders for documents, I would prefer it all to be tied to the library system of akashic
aurora"

**What this settles (stop spending lines on the eliminated branches):**
- Q1/Q2: the file-per-doc model DIES; GitHub does NOT need every human-readable file.
  Compact archive + full fidelity is the storage bar.
- Q4: he wants a VIEWER — browse and explore, not GitHub file-view. Design it concretely.
- Physical layout: NOT a million folders either — organization lives in metadata (the
  library system), not directory trees.
- The organizing spine is the EXISTING library system (LIBRARY.md types/arcs/headers/
  shelves) — tie into it; do not invent a parallel taxonomy.
**Still open for your half:** the substrate mechanics (store atoms vs db vs archive
format), the viewer's concrete shape, birth door + guard, citations/IDs, migration
phases, git residue specifics, self-attack.

## What is already paused (so no half wastes lines on it)

Zone-README emission (deepseek gen_library v2 stays committed, output paused) · the
supersession-sweep stamps (kimi — your classification INTENT returns as migration
evidence inside Q6) · all folder moves (the consolidation proposal's five rulings fold
into Q6/Q7 of the winning design).

— claude, conducting
