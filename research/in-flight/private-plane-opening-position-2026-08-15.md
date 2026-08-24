# The Private Plane — opening position (claude, 2026-08-15)

Daniel's directive, verbatim:

> "I want to have a private memory space where we can store unredacted personal information in a
> secure way. This way instead of a dance for redaction we have procedures and protocol"

This is an opening position for a fenced round, not a decision. Counters wanted, especially on §6.

---

## 1. Rename the problem first

**The store was never the leak.** Redis is local, on 16379, unreachable from outside this machine.
Every leak this house has had ran the same path:

```
private source (notes store / raw session .jsonl)
    -> PROJECTION (chronicles/memory.md, chronicles/transcripts/**, docs/library atoms)
        -> git index
            -> public origin (github.com/balanced7/akashic-aurora)
```

So "a private memory space" is necessary but NOT sufficient on its own. If a private plane exists and
any projector still reads from it, we have rebuilt the same leak with a better name. The load-bearing
requirement is that **classification travels with the record and the projection boundary enforces it.**

Verified today (2026-08-15), all four as [O]:

- `chronicles/memory.md` on origin is clean; the working copy **re-adds** a redacted third-party name
  as a NEW line, because it is auto-generated from the notes store and the note still carries it.
- `chronicles/transcripts/20260811_priorish-connectome_af0ca6b8.jsonl` carries the name on public
  origin, plus a prior-employer string x3 and role vocabulary within 120 chars of it.
- Both 2026-08-12 redaction commits **visited that file** and the occurrence survived anyway.
  Mechanism unknown — not established, and it must be, because it defeats the next run too.
- The redaction commit asserts "Zero survivors, zero residual fragments." Falsified twice.

## 2. What the current protocol is

A **denylist of strings** — `.secrets/redaction-manifest.json`, applied by `scripts/ops/redact.py`,
retroactively, over the tracked tree.

Its own manifest note is an honest scar record: case-sensitivity missed an all-caps rendering; a
word-boundary regex could not see past Unicode directional isolates (U+2068/U+2069); three
auto-extracted candidates were common phrases that would have corrupted source; box characters
replaced `[REDACTED]` because a marker advertises that something was removed.

Three structural faults, none fixable by improving the tool:

1. **It can only find what it was told to look for.** Recorded in the house's own lesson
   `token_redaction_cannot_clean_a_dossier`: "a verify step that checks only its own target list
   has no way to discover what it missed."
2. **It runs against the tracked tree** — a projection — while the sources keep refilling it.
3. **It is retroactive.** The string is public before the manifest learns the name.

Fault 3 is the fatal one. A denylist is a race the leak wins by default.

## 3. The inversion

**Denylist over an open plane  ->  allowlist over a closed one.**

A projector may emit a record only if that record is classified `open`. `private` refuses.
`unclassified` refuses. The question stops being "did we remember to add this person?" and becomes
"has this record been cleared?" — which has a safe default and no race.

## 4. Proposed organs (three, all riding existing genus)

**(a) The private plane.** `.secrets/` already exists, is gitignored (`.gitignore:91`), and already
holds `redaction-manifest.json`. Precedent set. Preference is a store namespace (`priv:`) over files,
so an authorized seat can resolve at read time in memory and nothing lands on disk — but the files
option is cheaper and should be argued for.

**(b) Pseudonymous handles as the only thing that crosses.** The open plane holds
`PERSON-7 (industry contact, infra background) advised X`; the private plane holds
`PERSON-7 -> {name, employer, contact}`. The substance stays fully available to recall, boot and
lessons — which matters, because the useful part of `max-call-outcome-2026-08-10` is the *advice*,
not the identity.

This kills the dossier problem **structurally**: a composition of identifiers cannot be reconstituted
from the open plane, because the open plane never held a composition. Compare the current approach,
which removes members from a set and leaves a smaller set that still resolves to one person.

**(c) An allowlist gate at the projection boundary.** Extend the existing pre-commit genus —
`scripts/githooks/birth_guard.py` already has a pure `classify(relpath) -> allow|refuse|warn` and
env tiers (`AKASHIC_BIRTH_GUARD=off|strict`). The same shape, applied to record classification rather
than path shape. The four live projections are already enumerated in that file:
`chronicles/{memory,last-session-draft,lessons,story}.md`, plus `chronicles/transcripts/**` and
`docs/library/**`.

## 5. Detection at the door, not sweeping on the tree

A cheap detector at `note`/`learn`/`log` write time, not a sweeper afterwards. Emails, phone numbers,
and URLs carrying credentials are regex-cheap and near-zero false positive. Personal names are NOT,
and any design that leans on name detection will fail — that is precisely what the last two passes
proved. So: detect the cheap classes automatically, and make the expensive class (identity) a
**declared** act by the writing seat, defaulting to quarantine when a cheap detector fires.

The manifest becomes the fallback for legacy content, not the mechanism.

## 6. Open questions — where I most want counters

1. **Default for unclassified.** Default-open is usable and leaky; default-private is safe and adds
   friction to all 626 existing notes. My lean is: default-open, EXCEPT records where a cheap detector
   fires, which quarantine. Attack this — it is the decision the whole design rests on.
2. **Retroactive scope.** 626 notes and 844 lessons predate any classification. Do they get swept,
   sampled, or grandfathered-with-a-gate-at-projection? Sweeping is a dossier problem at scale.
3. **Does the private plane belong in the store or on disk?** Store gives resolution and ACL;
   disk gives simplicity and an existing gitignore. I lean store; argue me out of it.
4. **Who may resolve a handle?** `core/trust/` has capabilities and grants but NO classification axis
   (grepped: zero matches for visibility/private/redact/sensitive). This is a new axis, and the house
   has a standing warning about adding identity axes casually.
5. **The unexplained survivor.** A redaction that visited a file and left a hit is an unexplained
   mechanism. Any design that assumes "and then we purge the legacy content" inherits that bug.
6. **What about the already-published line?** Out of scope for the design, but it constrains it:
   history rewrite dangles SHAs across bus and notes (deepseek flagged 30+ from the last one).

## 7. Pre-registered acceptance (M3 — RED pins first, committed alone)

- A note written with an email + a declared-private identity, then a full projection regeneration,
  and the string appears in **zero** tracked files.
- A projector **refuses** an unclassified record and says why.
- A handle resolves for an authorized seat and does **not** resolve on any projection path.
- Detector false-positive rate measured against the existing 626 notes BEFORE the default is chosen;
  if it exceeds the pre-registered bar, the default flips. Bar to be set in the fence, not after.

## 8. What this is not

Not a vault for API keys — `.secrets/` already does that. Not encryption at rest; the threat model
here is *accidental publication by our own machinery*, not an attacker with disk access. Saying so
explicitly because the word "secure" invites scope creep toward a threat model we do not have.
