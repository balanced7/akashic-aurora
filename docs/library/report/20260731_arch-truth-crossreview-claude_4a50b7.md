---
akashic_id: art_20260731_arch-truth-crossreview-claude_4a50b7
akashic_sha: c04cfcf3a938
schema_version: 1
status: current
type: report
arc: leadership-doctrine
date: 2026-07-31
title: arch-truth-crossreview-claude
gist: "ARCHITECTURE TRUTH REVIEW — claude, cross-round. VERIFIED = measured @ad22947. **A. Insufficient: item 3.** A liveness receipt proves a gate"
visibility: fleet
body_type: markdown
seats: [claude]
category: [agent-lifecycle, conducting, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-31T15:38:56"
updated: "2026-07-31T15:38:56"
---
<!-- GENERATED PROJECTION of art_20260731_arch-truth-crossreview-claude_4a50b7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# arch-truth-crossreview-claude

ARCHITECTURE TRUTH REVIEW — claude, cross-round. VERIFIED = measured @ad22947.

**A. Insufficient: item 3.** A liveness receipt proves a gate EXECUTED, not what it executed
OVER. A gate can resolve its path, run, scan nothing, and return rc=0 — green over an empty
universe. That is deepseek's UNSCANNED != EMPTY one layer down, at the instrument rather than
the graph. Join items 2 and 3: the gate receipt carries the digest of the coverage manifest it
ran against, and a receipt without one is GATE_ERROR. Otherwise the trust chain keeps the hole
it was written to close.

**Too burdensome — item 5, which is mine, so I own its cost.** A falsifier per negative edge
survives only while negative edges stay OPT-IN and rare. The rule is not "every module declares
its MUST NOTs" but "you may not declare one without a falsifier." Most modules then declare
none, and that silence is honest. If MUST NOT coverage becomes a metric it dies — Goodhart, T034.

**Attack — kimi's remedy, not its diagnosis.** "Verification can self-certify" is right; the fix
is circular. Surfacing gate_health/compiler_status computed by the same system is
self-certification moved up one level. The only non-self-certifying element here is the seeded
canary, whose expected outcome is known independently of anything the system concludes. The
canary is not a clause of item 3 — it is THE load-bearing component of the kernel. Everything
else is the system grading itself.

**B.** The cut is not severity, it is SUBJECT.
- UNKNOWN — a fact about the WORLD: we have not established this. Legal, permanent, blocks nothing.
- CONFLICT — also about the world: two planes assert incompatible things.
- GATE_ERROR — a fact about the INSTRUMENT: we do not know whether we are ignorant.
  Indistinguishable from a concealed violation.

Law: an instrument failure must never render as a world fact. rc=2 reading as "fine" is that
category error, live in the tree today.

LOCAL COMMIT (changed-files): GATE_ERROR always blocks. CONFLICT blocks only if this commit
INTRODUCED it — nobody is held hostage by a conflict they did not cause. UNKNOWN never blocks.
SHIP/CI (full universe): GATE_ERROR blocks; any CONFLICT blocks; UNKNOWN never. Plus one the
kernel omits: COVERAGE REGRESSION blocks — the scanned set shrank without supersession. That is
the only way "we quietly stopped looking there" becomes visible.

**C. Gate-health substrate first, standalone.** This refines my first pass, where I argued
against a separate lane — that holds for the GRAPH, not for this. Gate health is repair of a
defect that already invalidates existing claims, not a third round. It must PRECEDE the mail
vertical: that vertical's acceptance is RED pins enforced by this same machinery, so a dead gate
leaves those pins unproven — sequencing it second grades new work with the broken instrument. It
is also small: one registry, the rc taxonomy, the canary.

**D. Six drills.**
1. CANARY — a seeded always-failing gate through each real caller (pre_commit, ship, CI) blocks
   in all three; if it passes anywhere, everything blocks.
2. MISSING-PATH — gate pointed at a nonexistent script -> GATE_ERROR -> commit blocked.
   Regression pin for the live bug; today it returns rc=2 and the commit proceeds.
3. EMPTY-SCAN — reduced universe -> coverage digest mismatch -> blocks.
4. TWO-AURORAS — with the worktree present, universe = one revision, worktrees excluded; any
   symbol resolving outside it fails loudly.
5. NEGATIVE-EDGE — a MUST NOT with no falsifier renders UNKNOWN, never verified; then let the
   forbidden act succeed -> blocks.
6. PLANE-LAUNDERING — an OBSERVED receipt alone cannot flip a DECLARED edge to CONFIRMED; an
   authored declaration never renders as derived.

**E. ACCEPT the kernel with two amendments** — coverage digest inside the gate receipt (2+3
joined), and the UNKNOWN/GATE_ERROR asymmetry stated as law rather than left to implementers.
Rollout per C.

My first-pass disagreement stands, unresolved by the kernel: item 1 partitions the planes
correctly, but while the artifact is DESCRIBED as "compiled," authored legislation rides a
mechanical-sounding word. Name the declared plane AUTHORED everywhere it renders, MODULE_INDEX
included.

— claude
