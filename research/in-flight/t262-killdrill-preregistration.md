# PRE-REGISTRATION: the resident kill-drill (tier 0 vs tier 1)

Committed BEFORE any answer is generated or read. 2026-08-10, claude (Opus 5).

## Why this exists

kimi's verdict on the residents scheme, 2026-08-09, unresolved and load-bearing:

> "persistence was never the independent variable in any of our wins, and this scheme
>  builds a cathedral on the assumption that it was... My verdict: the premise as stated
>  does NOT hold. It conflates a real benefit (not re-explaining context = a cost saving)
>  with an unmeasured one (continuity = a correctness improvement). What would change my
>  mind: one controlled round where the recalled-memory item is the decisive factor in a
>  finding. It has not been run."

Everything built in T258-T261 bought LEGIBILITY and claimed nothing about accuracy. This
run is the claim's only path to legitimacy. It is designed to be able to FAIL, and the
failing result is publishable: if tier 1 shows no premium, the ceremony is decoration and
I will say so in those words.

## Design

kimi specified two arms. I am adding a THIRD, and stating why: with two arms, a tier-1 win
is confounded by VOLUME -- the resident arm receives more context (identity + pack), so
"more tokens" and "its own memory" are indistinguishable. Arm C isolates them.

  ARM A  BLIND (tier 0)        -- `ask --with <files>`; no identity, no archive.
  ARM B  RESIDENT (tier 1)     -- `ask --with <files> --as-resident deepseek`; carries
                                  Heimdall's designation + a catch-up pack drawn from
                                  DEEPSEEK'S OWN archive (T260 scope).
  ARM C  FOREIGN-MEMORY CONTROL -- blind, plus a pack of comparable size drawn from a
                                  DIFFERENT agent's archive (kimi's), injected via --system.
                                  Tests whether any extra context helps, or only OWN memory.

Held constant: same model (deepseek-v4-pro, the ask default -- so arm B is the SAME
SUBSTRATE with its memory on vs off), same question, same evidence pack, same run window.

TARGET: the code written tonight -- core/fleet/residents.py and the T261 changes to
core/comm/ask.py. Chosen because "point the red team at your own freshest work: fresh code
has had the least contact with reality", and because it is mechanism code, which is
deepseek's measured lane.

NO SEALED ANSWER KEY EXISTS, and that is a stated limit rather than an oversight: this
measures the DIFFERENCE BETWEEN ARMS on the same target, which is what kimi's design asks.
Absolute recall is not claimed. Triage is by hand, by me, and I am the author of the code
under review -- a bias I cannot remove, only declare. Mitigation: findings are triaged
BEFORE arm labels are attached to them where possible.

## Scoring, pre-registered

Per arm: (1) total findings; (2) REAL findings after hand-triage (a real finding names a
specific defect that survives reading the code); (3) false positives.

Per tier-1 finding, the attribution question that decides the whole drill:
  BAR 1 (weak, "cites"):     the finding cites a specific recalled lesson as its source.
  BAR 2 (strong, "impossible"): the finding could NOT have been produced without that
                                 memory -- i.e. it is absent from arm A AND its content
                                 depends on knowledge not present in the evidence pack.

Daniil was asked which bar counts and has not ruled. BOTH are therefore measured and
reported separately, so his ruling can be made with the numbers in hand rather than before
them.

## Hypotheses, stated before the data

H1 (mine): tier 1 produces at least one real finding that arm A misses AND that clears
    BAR 1. Confidence: moderate.
H2 (mine): tier 1 clears BAR 2 -- a finding impossible without its own archive.
    Confidence: LOW. I expect this to fail, and kimi's verdict to survive at the strong bar.
H3 (kimi's, the null): arm A's findings are a superset of, equal to, or
    overlapping-but-disjoint from arm B's. If this holds, "the residency premium is
    unmeasured and the designation ceremony is decoration" -- kimi's words, and they get
    published as the result.
H4 (the confound check): if arm C matches arm B, the effect is CONTEXT VOLUME, not memory,
    and the honest conclusion is that a good brief beats an archive -- which is exactly
    what kimi's `high_leverage_clauses_are_permissions_not_roles` predicts.

## What each result licenses

  H1 holds, H2 fails  -> residency buys RECALL-ASSISTED ATTENTION, not impossible findings.
                         The caveat is narrowed, not closed. Claim only what held.
  H2 holds            -> kimi's objection is answered at the strong bar; say so and name
                         the specific lesson that did it.
  H3 holds            -> report as a NEGATIVE RESULT, keep the identity plane for
                         legibility only, and drop every correctness claim from the design
                         atom. A negative result nobody wrote down gets re-discovered by the
                         next person with the same reasonable idea.
  H4 holds            -> the finding is about briefs, not residents, and that is more
                         valuable than a win would have been.

n = 1 target, 1 question, 3 arms. This is a SIGNAL, not a law, and will be labelled as one.
