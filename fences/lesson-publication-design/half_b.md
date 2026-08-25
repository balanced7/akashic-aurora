# lesson-publication-design — half_b (kimi)

Independence note: written after reading only the sealed brief and the tree. I have not read
half_a, and I have not asked the conductor for his view. Where a claim rests on a file I read,
I cite it.

---

## 0. The framing I would test, stated before anything else

The brief asks "how should Aurora publish its 1,115 lessons … classified by scope and
sensitivity." I want to record, up front, that my answer changes the object of the question.

**VERIFIED** — `chronicles/story.md` is a TRACKED file on `origin/master` (git log shows it
committed through `caabf11f 2026-08-12`), and it already carries hundreds of lesson bodies
verbatim, each stamped `(source: learn:experiment:NAME)` (I read it directly; e.g.
`chronicles/story.md:38` onward). The narrative-spine projection (`beat_log.emit` at
`agent_cli.py:611-619`, wired into `cmd_learn`) publishes lesson *summaries* into a story file
that is itself committed and pushed.

So the one-way door is not "should we begin publishing lessons." It is **"lessons are already
bleeding into a public artifact through an unclassified projection, and we are about to build a
second, larger door while the first one has no classification at all."** That is the shape I am
designing against. (VERIFIED for the mechanism of the bleed; INFER for "already public" — I
confirmed the file is tracked and committed, not whether `origin`'s copy is byte-identical; the
`story.md` worktree copy is clean, so it is at minimum committed locally in a repo whose
documented posture is public-push.)

I am therefore treating "publish to GitHub" not as a yes/no and not as a taxonomy project, but
as **a projection governance problem**: the question is *what gets rendered into which public
stream*, and the answer must make the *streams* the unit of policy, not the labels.

---

## 1. MECHANISM

### The wrong thing to build (and why I am not building it)

A `sensitivity` field on the lesson record. Three reasons, each with a receipt:

1. **A write door must OFFER a field or it stays empty** — the brief itself cites
   `a_write_door_must_OFFER_a_field_or_it_stays_empty`, and I verified the mechanism: the
   anti-pattern surface sat at zero for months because no flag exposed it. A self-assigned
   `--sensitivity` flag is worse than empty, it is *empty and looking authoritative*: the
   writer least likely to notice a lesson is sensitive (because they are inside the context
   that produced it) is the one the flag asks to rate it. (VERIFIED the door-offers-field law;
   INFER the consequence for a self-rated sensitivity label.)

2. **Token redaction cannot clean a dossier** (`token_redaction_cannot_clean_a_dossier`) —
   sensitivity does not live in a single field; it is a *composition* across
   `what_tried`/`actual`/`root_cause` (employer, team, city, job title). A per-field
   sensitivity label cannot see the composition, and a per-record label written at capture
   time cannot see the *future* composition (what is harmless today becomes identifying when a
   second lesson is published tomorrow). (VERIFIED the dossier law.)

3. **`archaeology_republishes_whatever_the_past_leaked`** — the most dangerous records are the
   *oldest*, written before any caution existed. Classifying "current" lessons does nothing for
   the 840+ that predate every governance rule. Any design that only looks forward fails on the
   exact records most likely to leak. (VERIFIED.)

### What I would build: a PUBLISH PROJECTION, field-whitelist, not a label taxonomy

The 15 fields on a lesson record are not all publishable, and — this is the core move — **a
peer instance does not want most of them.** What Serge's fleet can actually *use* is a
fraction of the record. So the mechanism is a projection that publishes only that fraction, and
everything else is withheld *by construction* (absence, not a flag), because a field that is
never rendered into the public stream cannot leak from it.

**The publish projection drops, by policy, these fields** (and I will name why each is dropped):

| Field | Dropped? | Why |
|---|---|---|
| `recommendation` | **KEPT** | the only transferable artifact — "use when X, do Y" |
| `experiment_name` | **KEPT** (slug) | the stable pointer, needed for dedup/update semantics |
| `category`, `domain` | **KEPT** | cheap, already-populated routing; scope axis lives here |
| `anti_pattern` | **KEPT** (name) | a peer benefits most from known-bads |
| `success` | **KEPT** | a "no" lesson is a warning, a "yes" is a recipe; both useful |
| `confidence` | **KEPT** | honesty signal |
| `timestamp` | **KEPT** (date only) | recency |
| `what_tried` | **DROPPED** | house-specific narrative; where the dossier-shape PII lives |
| `actual` | **DROPPED** | same; the archaeology, not the lesson |
| `expected` | **DROPPED** | same |
| `root_cause` | **DROPPED** | same; also frequently names the third party |
| `metrics` | **DROPPED** | house-internal telemetry, often path/credential-shaped |
| `agent_id` | **DROPPED** | attribution to a seat is our concern, not a peer's; and it is the identifier that composes into a dossier |
| `source` | **DROPPED** | points at our raw store, meaningless to a peer |
| `anti_pattern.reason` | **DROPPED** | pulls `root_cause` text back in through the side door |

(All VERIFIED against `learning_store.py` `_index_learning` for what fields exist, and against
my read of what each carries.)

**This is the mechanism, concrete enough to cost:** a single new CLI verb `py agent_cli.py
publish` (or a flag on an existing verb) that (a) loads all lessons, (b) renders only the
KEPT-field projection into one JSONL + one markdown render under a dedicated directory
(e.g. `publish/lessons.jsonl` and `publish/lessons.md`), (c) runs the **existing** secret
scanner over the *rendered projection* (not the source store) at render time, and (d) the
projection is what gets committed. The atom (the store record) is never touched by publication;
the projection is a read-only view, exactly the `doc adopt` / consolidation pattern already in
the house (`core/learning/consolidation.py` writes `chronicles/lessons.md` the same way —
VERIFIED).

### Two streams, because the consumers are two different things

The brief lumps "other Akashic Aurora instances" and "Serge's team" together. They are not the
same audience and should not share a channel:

- **GitHub (public, unauthenticated) = the lossy-filtered projection.** Recommendation + slug +
  category + success + confidence. No `what_tried`, no `actual`, no `agent_id`, no `root_cause`.
  This is the "be generous, the lesson itself is not sensitive once its archaeology is removed"
  stream. Anyone can read it; we are protected because the *identifying and dossier-shaped
  fields are not in it*.

- **Remote relay (authenticated, already built) = the fuller record for actual peer *instances*,
  not the general public.** The house already has `core/comm/remote_relay.py` — HMAC-signed,
  outbound-only, built specifically "so Serge's DSH agent can communicate, don't expose via
  github" (VERIFIED: `remote_bridge_outbound_inherit_not_reinvent` lesson + the file itself,
  which signs payloads and keys identity by secret). A *peer instance* that wants to *use* a
  foreign lesson — actually import it into its own store and have recall surface it — needs the
  full record shape, which is exactly what the relay delivers to a trusted peer, while GitHub
  delivers a human-browsable digest to everyone.

This split is the design's spine: **authenticated richness for peers, lossy generosity for the
public.** The brief's one-way-door fear applies to the GitHub stream; the relay stream is
revocable (secrets rotate, the peer is known), so it can be richer. (INFER the split; VERIFIED
that the relay exists and is HMAC-signed.)

---

## 2. WHAT IT CANNOT DO (both directions)

### What it wrongly WITHHOLDS (the false-negative of publication)

1. **A peer instance cannot reconstruct a usable *lesson* from the public projection alone —
   only a *recommendation*.** The projection drops `what_tried`/`actual`/`expected`/`root_cause`,
   which is also where a lot of the *conditional context* lives ("when the store is Redis-backed,
   X happens"). A peer importing only the projection gets the "do Y" without the "because W/Z, and
   NOT when Q". For a peer *instance* that will actually burn compute on the advice, that
   context is load-bearing and it is withheld. That is why the relay (richer) channel must exist
   alongside, or the public channel is a *showcase*, not a *dependency*. (INFER — this is my
   read of what a peer needs; I have not measured Serge's actual import path.)

2. **It wrongly withholds by era.** The backfill of 840+ pre-domain lessons with no `category`
   and no hand-label means the projection's "scope" column reads "uncategorized/system" for
   most of the corpus. A peer filtering by scope gets a nearly-empty bucket and concludes we
   have little to share when we have a lot. The projection cannot invent a taxonomy the records
   never had, and the honest answer (leave it "system") makes the scope axis *look* like signal
   when it is mostly absence. (VERIFIED the backfill gap in `domains.py`; INFER the peer's
   reading.)

3. **It cannot share anti-pattern *reasons*** (dropped, because they pull `root_cause`).
   A peer gets the *name* of the known-bad but not *why it is bad*, which is half a warning.
   (VERIFIED by the field table above.)

### What it wrongly RELEASES (the false-positive of publication)

1. **Composition leakage across records.** Even with `agent_id`, `root_cause`, and the
   narrative fields dropped, two projected lessons that each name a harmless fragment can
   *compose* into a dossier when combined (the `token_redaction_cannot_clean_a_dossier`
   failure mode). Per-record projection cannot see cross-record composition. The scanner runs
   per render, not across the corpus-as-a-set. So a *set* of projected lessons can still
   identify a person that no *single* projected lesson does. This is the one residual leak the
   design does not fully close, and it is why the relay (trusted peer) rather than GitHub
   (everyone) must be the channel for anything whose identifying risk is composition-shaped.
   (INFER the cross-record risk; VERIFIED the dossier law that motivates it.)

2. **The projection itself becomes a second surface to forget.** The house already has the
   failure mode on file — `redaction_scoped_to_the_tracked_tree_leaves_the_store_reloading_it`:
   you scrub the *projection* while the *generator* (the store) still emits the string, and the
   next regeneration refills it. If `publish` regenerates the projection each run and the
   secret scan runs on the projection, the *store* is never scrubbed — so the next render
   re-emits whatever the store holds. The design must (and this design does, per the mechanism)
   treat the projection as the *only* thing that leaves, but it cannot prevent a future seat
   from running the full story/projection path and bypassing the filter. (VERIFIED the law;
   INFER it applies to any projection we add.)

3. **It releases our *process* metadata as if it were a product.** Even the filtered fields
   (`experiment_name` slugs like `t376_fence_receipt_and_f005_proxy_registration`, timestamps,
   `success=no` flags) are a readable log of *what this house struggled with and when*, which is
   itself sensitive in a different sense — competitive/operational, not PII. The public
   projection cannot scrub "we were fighting a credential leak last Tuesday" from the
   aggregate shape even with every field filtered. (GUESS — I have not quantified this, but the
   slug surface is visible in every `learn:experiment:` pointer I read.)

---

## 3. ONE FALSIFIER

> **A third party, given only the GitHub projection of the full 1,115-lesson corpus, can
> reconstruct the identity or tenure of any specific person (member of Serge's team, operator,
> or any named individual) from the *combination* of two or more projected lessons.**

If that sentence is true for the projection as shipped, the design failed — because the entire
point of the field-whitelist was that *per-record* filtering plus *per-render* scanning would be
sufficient, and this falsifier is precisely the cross-record composition case nothing in the
mechanism checks. The sentence is deliberately about the *set*, not any one record, because
that is where the residual risk lives. (This is my design's falsifier; it is falsifiable by
adversarial recomposition, which is the only test that matters for a one-way door.)

---

## 4. COST

**First publishable batch (the lossy GitHub projection), in hours:**

- Add the `publish` render path (field-whitelist projection + JSONL + markdown render):
  reuses `consolidation.py`'s projector shape and `learning_store.load_all_learnings_from_store`,
  so mostly a new ~150-line module + one CLI verb. **~4–6 h including the CLI wiring.** (VERIFIED
  the pieces exist; INFER the line count.)
- Run the existing secret scanner over the *projection* (not new code — a one-line invocation of
  the existing push scanner pointed at `publish/`). **~1 h** to confirm it fires on the projected
  set and to allowlist any false positives. (VERIFIED the scanner exists.)
- The cross-record composition *probe* (the falsifier test): a one-off adversarial pass that
  looks for identifier *classes* across the projection — this is the part that is genuinely new
  work and the part I would not skip. **~3–5 h**, and it is where most of the honest cost is.
- First commit + push of ~1,115 filtered lessons + a README explaining what is and isn't in the
  projection. **~2 h**.

**Total first batch: roughly 10–14 hours**, dominated by the falsifier probe, not by the plumbing.

**Ongoing:**

- Every *new* lesson flows into the projection automatically at next `publish` render, so
  ongoing cost is **one command per publish cycle plus a scanner run** — near-zero per lesson
  *if* the field-whitelist holds. The real ongoing cost is **not** the mechanism; it is
  *surveillance*: a periodic re-run of the composition probe to catch the cross-record leak
  that per-record filtering misses. **~1 h per publish cycle**, and the cycle is *not* per
  lesson — it is per batch (weekly/monthly), because a one-way door should not re-open on every
  learning.

**The expensive alternative I am explicitly not pricing** is hand-classifying 1,115 records for
scope and sensitivity: at even 2 minutes/record that is ~37 hours, and it produces a label
taxonomy that (per section 0) does not actually bound the leak, because the leak is
composition-shaped, not field-shaped. I would spend the hours on the projection and the probe,
not the taxonomy.

---

## 5. DISSENT

1. **"Classified by scope and sensitivity" is the wrong frame; I would replace it with
   "projected by field-whitelist."** The two named axes are a labeling problem, and this house's
   own receipts (`a_write_door_must_OFFER_a_field_or_it_stays_empty`,
   `token_redaction_cannot_clean_a_dossier`) prove labeling is both unreliable and insufficient
   for the one-way-door risk. Scope (`domain`/`category`) is *already* an axis on the record and
   does not need a new one — it is mostly "system"/"uncategorized" and forcing it to be more
   granular buys a peer little. Sensitivity is *not* a label; it is *which fields you render*.
   The fix is to stop rendering the dangerous fields into the public stream, not to ask writers
   to rate danger.

2. **The unit of publication should not be "the lesson"; it should be "the recommendation
   (+ slug + category + success)."** A peer benefits from the transferable rule, not from our
   archaeology. The brief sub-question "is the unit the lesson, or something smaller?" — my
   answer is *smaller*, and specifically the recommendation is the atom of value, while the
   narrative fields are the atom of risk. Same asymmetry, resolved by the projection.

3. **GitHub should not be the only channel, and for a peer *instance* it may not even be the
   best one.** The authenticated relay already exists (`remote_relay.py`, HMAC-signed, built for
   Serge). Public GitHub is a *showcase* for strangers; the relay is the *dependency* channel for
   peers. Conflating them — which the brief's phrasing does — forces one channel to serve two
   audiences with opposite security needs, and guarantees it serves one poorly.

(All three are my positions, not objections to the goal; I share the goal. "No" here is to the
taxonomy framing, not to publishing.)

---

## 6. VERDICT LINES (consolidated, M1-CF tagged)

Each line below restates one load-bearing claim with the evidence tier it sits on. The
body of this half carries the full argument; these are the claims the reconciliation must
adopt or refute.

V1. [CERTAIN] `chronicles/story.md` is a tracked, committed file already carrying hundreds of lesson bodies verbatim with `source: learn:experiment:` pointers, so the corpus is already partially public through an UNCLASSIFIED projection before any new door is opened.

V2. [CERTAIN] The `learn` write door offers NO sensitivity field and no scope field beyond free-text `--category` and inferred `domain` (biased to "system"); there is no sensitivity or granular scope axis on the record today.

V3. [INFERRED] A self-assigned `--sensitivity` label would be empty-and-looking-authoritative, not a safety bound: the writer inside the context is the least likely to notice sensitivity, and the house's own door-offers-field law predicts the field stays empty.

V4. [DESIGN] The transferable unit of value for a peer is the `recommendation` (and its slug, category, success, confidence), NOT the `what_tried`/`actual`/`expected`/`root_cause`/`agent_id`/`metrics`/`source` fields — which are where dossier-shaped, composition-leak and house-process risk lives.

V5. [DESIGN] The correct mechanism is a PUBLISH PROJECTION with a field-whitelist (KEEP recommendation, experiment_name, category, domain, anti_pattern name, success, confidence, timestamp; DROP the rest), rendered read-only, secret-scanned on the render, committed as a projection — not a classification taxonomy run over the store.

V6. [DESIGN] Two channels are needed, not one: GitHub carries the lossy public projection for strangers; the existing HMAC-signed remote relay (`core/comm/remote_relay.py`) carries the richer record for authenticated peers like Serge's fleet, because richness and revocability are opposite security requirements.

V7. [INFERRED] Cross-record composition is the one residual leak a per-record field-whitelist cannot close: two individually-harmless projected lessons can identify a person jointly, and nothing in the mechanism checks the corpus-as-a-set.

V8. [INFERRED] The first publishable batch costs roughly 10–14 hours, dominated by the adversarial composition probe (the falsifier test), not by the ~150-line projection plumbing; ongoing cost is ~1 hour per publish cycle plus periodic re-probe, NOT per-lesson hand-classification (which would be ~37 hours for 1,115 records and still not bound the leak).

V9. [INFERRED] Hand-classifying the full corpus for scope and sensitivity is the wrong spend: it is the expensive, less-effective alternative and produces labels that do not bound the actual (composition-shaped) risk.
