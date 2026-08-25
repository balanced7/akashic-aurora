# half_a — lesson-publication-design — deepseek/Heimdall

Sealed 2026-08-25. Drafted before reading the conductor's synthesis or half_b.

Every verdict line carries exactly one M1-CF tag (CERTAIN / DESIGN / INFERRED / UNCERTAIN).
Supporting facts sourced from files are tagged VERIFIED; my readings INFER; assertions GUESS.

---

## RESTATEMENT, AGAINST THE EVIDENCE

Three measured facts reframe the question before I answer it:

1. **The repo is already public.** VERIFIED — `scripts/checkers/check_secrets.py` docstring:
   "the repo is PUBLIC, several agent seats hold commit access, and `.secrets/API Keys/` sits one
   gitignore rule away." There is no private-repo option being lost; the code is already out.
   Lessons are a NEW leak surface added to an already-open door, not the first one.

2. **The intended consumer's problem is not "read our lessons" — it is "catch up to us."**
   VERIFIED (operator verbatim, session `3e5f0bdf-2a14-48e2-a7d8-43ba848bf30e:4751`): "serge has
   his own dsh separate from ours on a completely different akashic aurora instance running off his
   laptop, they need the full integration specs and everything they need to catch up to us." A
   lesson corpus is a *partial* answer to "catch up"; a peer also needs the schema and the doors
   the lessons point at.

3. **The one-way door is not new.** VERIFIED — `core/world_seed.py` already models the asymmetry
   ("Downward is a copy; upward is a claim"), and `core/trust/private_plane.py` already found the
   sharper leak ("existence metadata is a leak").

So the real question is narrower: **what subset of the knowledge layer can be made a public
PROJECTION such that the one-time release is both useful and irreversible-safe?**

---

## VERDICTS

V1. MECHANISM [DESIGN] — publish a withhold-by-default PROJECTION off `learn:`, behind the two
existing egress gates, with provenance folded in.

The unit of publication is the LESSON record, minus its identity fields. A peer needs
`experiment_name`, `what_tried`, `recommendation`, `root_cause`, `anti_pattern`, `category`,
`domain`, `success`; it does NOT need `agent_id`, `timestamp`, `source`, or `metrics` (raw JSON
that can embed arbitrary strings). VERIFIED the schema admits all 15 fields at
`core/learning/learning_store.py` (~line 640); the exporter selects a strict subset. INFER that
stripping identity + metrics also strips most accidental sensitivity, because that is where a name
or inline blob tends to hide.

The mechanism mirrors two projections the house already trusts:
- `core/learning/vfx_chunk_lessons.py` (VERIFIED): adopt a source note as a lesson-shaped
  *projection*, keep the file as source of truth, key by name, re-runnable.
- `py agent_cli.py doc adopt` + `docs/library/` (VERIFIED): atoms are truth, renders are
  read-only regenerated — the exact contract the brief cites.

So publication is a THIRD projection: a generator walks `learn:experiments:all`, applies a
classifier + field-subset projection, writes Markdown/JSONL to `docs/library/lessons/`, re-runnable.
No new store, no two-truth drift. `scripts/ops/snapshot_knowledge.py` (VERIFIED) already proves the
dump/restore seam exists.

The classifier holds TWO SEPARATE axes (see V6 — sensitivity is the load-bearing one):
- **SENSITIVITY (the gate):** three-way, DEFAULTS-WITHHOLD.
  - `PUBLIC` — no private-plane marker, passes credential patterns, no dossier name.
  - `REDACTED-PUBLIC` — would be public but carries a private marker or credential shape; publish
    with the offending token visibly masked, reusing `core/comm/discord_bridge.py` `redact()` and
    `core/trust/private_plane.py` `scan_text()` (both VERIFIED; the latter is built exactly for "a
    blob of prose about to become durable and public").
  - `PRIVATE` — the default; anything not positively cleared stays home.
- The classifier is MECHANICAL, not model-jury: a lesson clears to PUBLIC only if (i) it carries no
  private-plane marker (reuse `private_plane.markers()` + `scan_text()`, VERIFIED), (ii)
  `check_secrets.py` finds no credential shape in the projected bytes (VERIFIED pattern-based, fast,
  already wired to pre-push), (iii) it carries no private dossier noun. GUESS on the operator-name
  rule: ordinary "Daniil ruled" is the house's public identity and should NOT be auto-redacted; the
  private-plane markers already carry the actually-sensitive nouns, and private_plane itself warns
  a too-generic marker (e.g. "daniil") "would refuse every commit in the repo."

Egress is the SAME two existing gates plus one new one:
- `scripts/githooks/pre-push` §4 (VERIFIED) already blocks credential-shaped content at push.
- Fold `private_plane` markers into a pre-push check over `docs/library/lessons/` so a regeneration
  that re-absorbs a private noun is caught at ship, not read back from public later — exactly the
  miss `private_plane.py` documents ("the leak path is REGENERATION, not authoring").
- NEW: the projection refuses to commit if a PRIVATE-marked lesson's title/body leaked into a
  PUBLIC render — the falsifier of V4 made executable.

A peer receives the corpus + a manifest that says what is missing: "N lessons published, M
withheld (PRIVATE default), K redacted; here is the classifier and how to open a lesson." This is
`core/world_seed.py`'s Dawe Test (VERIFIED: "reports what it REFUSED to copy and why") applied to
publication — the honest version of "we published but the good stuff is behind a door."

V2. WHAT IT CANNOT DO [UNCERTAIN] — it cannot guarantee a prose lesson contains no secret, and it cannot
stop a lesson from *naming* something private without containing it.

- **Wrongly RELEASES (the dangerous direction).** `check_secrets.py` is pattern-based and says so
  (VERIFIED docstring: "reduces exposure, it does not prove absence"). An arbitrary high-entropy
  string that is actually a password, written inside a `what_tried` sentence as prose, matches no
  shape. The classifier shrinks the blast radius; it does not close it. This is the single hardest
  residual and I do not paper it over.
- **Wrongly RELEASES (existence metadata).** A lesson saying "when fixing the `<private-slug>`
  integration, do X" leaks that `<private-slug>` exists even if its body is clean. `private_plane.py`
  (VERIFIED) already named this class. The marker scan catches derived markers, but a private
  concept never placed in `private/` has no marker to catch. GUESS this residual is smaller than
  the credential one but real, and only the larger two-store arc `private_plane.py` itself defers
  truly closes it.
- **It cannot be recalled.** Irreversibility is the premise. The design's answer is
  withhold-by-default (shrink releases, don't expand them) plus the manifest's honest "M withheld."

V3. WHAT IT CANNOT DO [UNCERTAIN] — a withhold-by-default classifier with no release path strands the
corpus, and the projection cannot make lessons *land* in a peer by themselves.

- **Wrongly WITHHOLDS (empty corpus).** The house's own law (VERIFIED, brief): "a write door must
  OFFER a field or it stays empty." Mirror it: a publish door must OFFER a release, or the corpus
  stays empty. Without a cheap `publish --lesson X` Daniil can run, nothing is promoted past
  PRIVATE and the public repo ships a near-empty `lessons/` — a door that publishes nothing is as
  much a failure as one that publishes everything.
- **Wrongly WITHHOLDS (over-redaction).** A peer-usable lesson is the recommendation tied to the
  thing it recommends against — the file path, the verb, the schema. If the projection over-redacts,
  it reproduces `discord_bridge.redact`'s own warning (VERIFIED: "over-redaction makes the channel
  useless, which is how a safety feature gets switched off"). Redact only identifiers of private
  things, never the technical content.
- **Wrongly PROMISES (bytes ≠ wiring).** A foreign lesson is inert text until the peer's store
  ingests it, and `core/world_seed.py` (VERIFIED) already refuses the naive path: an inward/upward
  lesson is "a rumor, not a fact," grounded against the peer's OWN store. Publishing to GitHub
  ships bytes, not wiring; the ingest path (`learn --from-file`, or a peer-side `world_seed` with
  provenance) is SEPARATE work this mechanism does not do. If we imagine Serge's dsh will
  auto-benefit, we are wrong.

V4. ONE FALSIFIER [CERTAIN] — "A lesson that should have been withheld became public through the
automatic projection, and nobody noticed until it was read back from GitHub."

If that sentence is ever true, the design has failed, because its entire premise is that
withhold-by-default + egress gates make a wrong release *loud at the ship moment, not silent after
it.* The executable form is the pre-push pin: no public-projection render carries a private-plane
marker or a credential shape. That pin stays GREEN exactly as long as the falsifier stays false. If
we ship the projection without wiring that pin to a gate that must RUN (not "can be run" —
`scripts/githooks/pre-push`'s own WHY section, VERIFIED, is the standing lesson that "a probe that
can also be not-run is not the fix"), we have shipped the failure condition as a feature.

V5. COST [INFERRED] — first publishable batch 6–10 hours; ongoing ~1–2h/month, and the real un-counted
cost is the peer INGEST path, not the publication.

- Classifier + projection generator off `learning_store`: 3–4h. New module reading
  `learn:experiments:all`, field-subset + two existing scanners, writes Markdown + manifest. The
  hard 10% is marker integration, not the writing.
- New gate + pin: 1–2h. The pre-push hook exists (VERIFIED); add §5 running the falsifier pin.
  Cheapest, highest-leverage slice.
- First human pass over the PRIVATE bucket that LOOKS safe: 2–4h, one sitting, recur once if the
  classifier is good. VERIFIED there is exactly ONE write door (`py agent_cli.py learn`), so the
  classifier hooks at ingress and the ongoing cost collapses to "default PRIVATE, flip PUBLIC when
  sure."
- Ongoing: ~1–2h/month — weekly projection re-run + `check_secrets.py --history` (the full-history
  sweep is already a documented weekly task, VERIFIED). The ongoing RISK cost (attention on the
  false-negative rate) is the real one; that is the only thing that turns this into an incident.
- NOT COUNTED, flagged as the real cost: the peer ingest path — `learn --from-file` with
  provenance grounding, `world_seed` marking imported lessons foreign/grounded:false. That full
  loop is GUESS 2–3 days, and the brief's "so peer instances can benefit" is only half-served by
  publication alone.

V6. DISSENT [CERTAIN] — three disagreements with the ask's framing, in order of consequence.

**DISSENT 1 — "to GitHub" may be the wrong channel for Serge, and Daniil already said so a day
earlier.** INFER (agent-transcribed, not operator-verbatim): lesson
`remote_bridge_outbound_inherit_not_reinvent` records Daniil 2026-08-24 as saying "connect remote
bifrosts so Serge's DSH agent can communicate, **don't expose via github**." VERIFIED (operator
verbatim) he said Serge needs "the full integration specs and everything they need to catch up."
The bridge that sentence describes — `core/comm/remote_relay.py`, VERIFIED built, with HMAC,
allowlist, redaction — is a *trusted, authenticated* channel between two Akashic instances.
Publishing lessons to public GitHub is a *different and strictly broader* exposure for a *different
and narrower* benefit (bytes, not wiring). My fence answers publication as asked; I will not seal
without recording that the same goal may be better served by shipping the `learn:` projection
THROUGH the existing remote relay to Serge, reserving public GitHub for the schema/docs/specs Serge
needs to catch up — which "catch up to us" implies and lessons do not contain. I did not ask the
conductor and did not read half_b.

**DISSENT 2 — "scope" as framed is a retrieval axis, not a publication axis.** VERIFIED in
`core/learning/domains.py`: "domains partition RANKING, not the corpus." Whether a lesson is
`system` or `vfx` decides where in OUR recall it fires; it says nothing about whether a peer may
safely read it — the only question a one-way door cares about. Sorting publication by scope sorts
by a field that does not measure the risk we pay for. The axis that matters for publication is
**transferability** (does this generalize past our mutant code?) — closer to `world_seed.py`'s own
warning (VERIFIED): "a lesson learned in alpha contains alpha's interpretation of alpha's mutant
code, so it is not a replayable input." If anything, the useful scope axis is
house-specific-vs-generalizable, which is not what the brief named.

**DISSENT 3 — sensitivity and scope are NOT one ladder, and "classify into buckets" undersells the
sensitivity half.** Sensitivity is a hard threshold (does releasing this hurt us); scope/transfer
is a soft gradient (how useful is it to them). Conflating them produces records that are both
"system" and "private," asking one category to serve a routing AND a safety decision. Keep them as
two fields on one record — the schema already has `domain`; add `visibility` — and let orthogonal
axes stay orthogonal. The scope axis is not wrong enough to discard, but it is the wrong basis for
the publication gate, which should be keyed on sensitivity alone.

---

*Sealed by deepseek/Heimdall. Half_b unread. Verdict lines V1–V6 each carry one M1-CF tag. The
falsifier is V4; the dissent is V6, awaiting the conductor's reconciliation.*
