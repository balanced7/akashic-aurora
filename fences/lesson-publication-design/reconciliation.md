# RECONCILIATION — lesson-publication-design

Both halves sealed blind. Conductor's synthesis was withheld from the brief and is disclosed
below only where it was WRONG, which is most of where it mattered.

## RULING 0 — a finding outranks the question that was asked

**half_b V1 [CERTAIN] is VERIFIED, independently, by me, just now.** `chronicles/story.md` is
**547,900 bytes, git-TRACKED, in a PUBLIC repo, carrying 822 `learn:experiment:` references
with lesson bodies verbatim**, and has been since at least 2026-08-12.

Daniil asked how to publish lessons safely. The answer begins: **822 of them already are, through
an unclassified projection nobody designed as a publication.** The one-way door did not need
opening. It has been open for two weeks.

This reorders the work. AUDIT WHAT ALREADY SHIPPED comes before DESIGN WHAT TO SHIP, because the
second is hypothetical risk and the first is realised. Neither half's mechanism helps with a
record already on GitHub.

I did not find this. My withheld answer designed a future publication on the assumption that
nothing was published yet. That assumption was never checked, and it was load-bearing.

## RULING 1 — ADOPTED, and it is the strongest signal in the fence

**Two channels, not one.** GitHub carries a lossy public projection for strangers;
`core/comm/remote_relay.py` (VERIFIED built: HMAC-signed, allowlisted, redacting) carries the
richer record to authenticated peers like Serge's fleet.

Both halves reached this **independently and by different evidence**: half_a from a recorded
operator line ("don't expose via github") plus the observation that a peer needs wiring rather
than bytes; half_b from richness and revocability being opposite security requirements. Sealed
blind, different routes, same destination. That is corroboration rather than the correlated
agreement I fenced against.

Consequence, adopted: publishing to GitHub and serving Serge are DIFFERENT JOBS. Conflating them
forces one channel to serve two audiences with opposing needs and guarantees it serves one badly.

## RULING 2 — ADOPTED: the mechanism is a FIELD-WHITELIST projection, not a label taxonomy

half_b's frame wins the default path. Sensitivity is not a label to assign; it is **which fields
you render**. KEEP `recommendation, experiment_name, category, domain, anti_pattern, success,
confidence`; DROP `what_tried, actual, expected, root_cause, agent_id, source, metrics` — the
narrative fields are the atom of risk, the recommendation is the atom of value.

**But half_a's V3 is adopted alongside it:** a publish door must OFFER a release or the corpus
stays empty, mirroring the house's own write-door law. Whitelist by default; an explicit
per-lesson opt-in promotes narrative when it is genuinely the value and has been cleared.

## RULING 3 — the conductor was WRONG, corrected from two directions

My withheld answer was: classify at the door with `--scope`, and genericise the evidence.

- half_b V3: a self-assigned sensitivity label is "empty-and-looking-authoritative" — the writer
  inside the context is the LEAST likely to notice sensitivity.
- half_a DISSENT 2 (VERIFIED against `core/learning/domains.py`): "domains partition RANKING, not
  the corpus." Scope is a RETRIEVAL axis. It decides where a lesson fires in OUR recall and says
  nothing about whether a peer may safely read it.

Both are right. The author can supply SCOPE; the author cannot supply SENSITIVITY. Daniil's two
axes are real but they are not both publication axes — scope routes, sensitivity gates, and only
sensitivity may hold the door. My genericiser survives, subordinated: it applies to whatever
narrative we deliberately publish, not as the primary control.

## RULING 4 — the residual neither I nor half_a saw

**half_b V7: cross-record COMPOSITION.** Two individually-harmless projected lessons can jointly
identify a person, and nothing in a per-record whitelist checks the corpus AS A SET. half_a's
residual (pattern scanners cannot prove absence) is real but smaller and already known;
composition is the one that defeats the whole mechanism's premise.

Adopted as the binding falsifier, because it is the only one that tests the SET:

> A third party, given only the GitHub projection, can reconstruct the identity or tenure of any
> specific person from the COMBINATION of two or more projected lessons.

## RULING 5 — COST: half_b's number, and the gap between them is the point

half_a 6–10h; half_b 10–14h. The difference is almost exactly the adversarial composition probe,
which half_a does not cost because it did not surface that risk. Take **10–14h**, and note
half_b's alternative costing: hand-classifying 1,115 records is ~37 hours **and still does not
bound the composition risk** — the expensive option is also the less effective one.

Both agree the UNCOUNTED cost is the peer INGEST path (half_a: 2–3 days, GUESS). Publishing ships
bytes, not wiring. "So peer instances can benefit" is half-served by publication alone.

## OPEN — TWO RULINGS THAT ARE DANIIL'S, NOT MINE

1. **story.md.** 822 lesson references are already public. What does he want: audit and leave,
   audit and scrub history, or accept and move on? This is a disclosure decision about material
   already released, and it is his call alone.
2. **half_a DISSENT 1.** A lesson records him saying, 2026-08-24, "connect remote bifrosts so
   Serge's DSH agent can communicate, **don't expose via github**." half_a marked it INFER
   (agent-transcribed, not operator-verbatim) and refused to seal without recording it. If that
   is what he meant, today's ask may contradict a ruling he already made. Only he can settle it,
   and a lesson cited as current state inherits its own timestamp.

## PROCESS NOTE

The fence worked exactly as designed and I want that on the record. My synthesis was withheld;
both halves were sealed blind; each brought a finding the other lacked; and BOTH corrected the
conductor in the same place from different directions. Had I written the brief with my answer in
it, the most likely outcome is two halves agreeing with me and nobody checking whether the corpus
was already public.

## M1-PV — premise verification (run BEFORE this seal, at the door's insistence)

**14 verified, 2 MISSING**, and the two are named rather than glossed:

- `half_b: publish/lessons.jsonl` — MISSING
- `half_b: publish/lessons.md` — MISSING

Both are **proposed output paths of a mechanism that does not exist yet**, not claimed existing
evidence. A design naming where its artifact would land is not a false premise; it would be a
false premise only if half_b had asserted they were already there, and it did not. Explicable,
benign, recorded.

The fence door refused my first seal because PV had not run. It was right to: I had read both
arguments and written a ruling before verifying their premises, which is the exact ordering
error the gate exists to prevent. That refusal is the seventh guard to catch me in two days, and
the second today to catch me before anything left the house rather than after.
