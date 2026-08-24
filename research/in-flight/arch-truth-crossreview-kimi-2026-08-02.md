# ARCH TRUTH REVIEW — kimi cross-round. Lens: cognition, status ambiguity, human factors.
VERIFIED = read in live tree this morning. INFER flagged. No consensus sought.

## A. Which kernel item is wrong / insufficient / too burdensome

**Item 3 is internally inconsistent — and I VERIFIED it in the tree.** The kernel says
"rc=0 pass, rc=1 violation, other/missing = GATE_ERROR." But the *fixed* `pre_commit.py` still
has at line 252–253: `rc, out = _comprehensibility_fast(); if rc == 1:` — it blocks ONLY on
rc==1. The new exists-branch returns rc=2 with a loud message, and the caller **does not block
on it.** So today: a MISSING checker prints "this gate is NOT running" and the commit PROCEEDS.
That is GATE_ERROR being treated as pass-with-warning. The kernel's rule is correct on paper;
the repo does not implement it. **Item 3 is insufficient until the caller blocks on rc != 0**
(i.e. GATE_ERROR blocks exactly like a violation). This is not a hypothetical — it is the same
ghost-path bug one layer down, still live: we made the absence LOUD but did not make it STOP.
[VERIFIED by reading 252–253 + the exists-branch.]

**Item 4 is the one that will be gamed into uselessness (my lens).** "Bypass/exemption =
visible DEGRADED edge" is right, but DEGRADED must not decay into background. A permanently
DEGRADED edge trains readers to ignore the label — the same way UNKNOWN-that-blocks trains
filler. DEGRADED needs an expiry or a ratchet count, else it becomes the new green.

## B. UNKNOWN vs GATE_ERROR vs CONFLICT — what blocks what

Three different epistemic objects, three different dispositions. The proposal currently lets
them blur:

- **UNKNOWN (epistemic)** = the layer cannot derive the answer. LEGAL, never blocks local
  commit, never blocks ship. It is a *true statement about coverage.* Making it block trains
  fabrication (the sealed-key lesson: UNKNOWN must score correct). Renders as an honest gap.
- **CONFLICT** = two sources both assert, and disagree (map says unbypassable, docstring says
  fail-open). Blocks **canonical ship/CI integration of the contested edge** — but must NOT
  block local commit, because the disconfirming source is usually authored locally and the
  commit is how it enters the record. Blocking the local write would suppress the evidence.
  Renders as both spans, unresolved, until a human rules.
- **GATE_ERROR** = the verifier did not produce a verdict (missing, crash, rc∉{0,1}). This is
  NOT a truth-claim at all — it is instrument failure. It must block the action the gate guards:
  **local commit (the write-edge hook) AND ship/CI**, identically to rc=1. The current tree
  violates this (§A). A GATE_ERROR that blocks less than a violation is a hole shaped exactly
  like a missing file.

One line: UNKNOWN = "we don't know" (allow); CONFLICT = "sources disagree" (hold the edge, let
the write through); GATE_ERROR = "the scale is broken" (stop the line, same as a violation).

## C. Rollout: gate-health substrate FIRST, standalone

Substrate first, and it is not close. Two reasons, one measured:
1. The directed-mail vertical is a *consumer* of trust language. Building it before the
   substrate means its first edges are compiled by the very apparatus whose GATE_ERROR handling
   is still wrong in the tree (§A). You would be calibrating the consumer against a broken
   scale.
2. The substrate slice is *self-checking*: its acceptance is a RED→GREEN pin on a gate that is
   currently misbehaving (rc!=0 not blocking). That is a kill drill you can run on day one
   against live infrastructure, no fixture needed. Mail offers no equivalent free oracle.
   [INFER on sequencing; VERIFIED that the rc!=0 gap is live and drillable today.]

## D. Smallest acceptance suite I would trust (four drills, no more)

1. **DEAD-GATE / rc-OUTSIDE-{0,1}**: point the hook at a missing checker → commit must FAIL.
   (Currently fails this drill — VERIFIED.) This is the one that proves GATE_ERROR blocks.
2. **CANARY**: a seeded always-fail gate invoked through the real caller; if the harness reports
   pass, everything blocks. Proves the harness runs gates at all.
3. **CONFLICT-VISIBILITY**: feed the map-vs-docstring pair (unbypassable vs fail-open) → edge
   renders CONFLICT, both spans linked, local commit proceeds, canonical ship of that edge held.
4. **COVERAGE**: scanner over a subset → UNSCANNED region renders UNSCANNED, never EMPTY
   (deepseek's condition; I endorse it as the cheapest of the four to pin and the most likely to
   be quietly dropped).
No fifth drill. If these four pass, the trust language may be *provisional*; the moment one
passes by a fixture rather than against the live tree, it does not count.

## E. Verdict after amendments: AMEND — accept the kernel, one blocking correction

**BLOCKING: make the write-edge caller block on rc != 0 (GATE_ERROR == violation at the
chokepoint), and pin it with drill D1, BEFORE any graph edge carries a trust label.** This is
smaller than claude's original gate-receipt condition and it is still unmet — the 2026-08-01
fix made absence loud, not stopping. I keep my round-1 status-provenance rule (§5 there) as a
*required amendment* but no longer blocking: it is item 4's correct elaboration.

**Attack, per invitation — on my own round-1 pass and on a shared misreading:** I accepted the
brief's "rc=2 is ignored because it blocks only rc==1" as *stale* because the path was fixed.
That was half-right. The path is fixed; the rc==1-only blocking is NOT — it is the live residue
and I under-weighted it. claude's "any non-zero exit blocks" was the right call and the tree
still does not do it; credit that to claude, and flag that BOTH my round-1 "fixed" framing and
any seat treating the 08-01 patch as closing the liveness condition are premature. Grok's
"documented unbypassable is itself a lie" stands and is now joined by a second live one:
"GATE_ERROR blocks" is documented in the kernel and not true in the hook.

— kimi
