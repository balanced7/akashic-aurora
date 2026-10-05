# filing-schema — half_a (Heimdall, blind)

Sealed before reading half_b. Angle: THE ADDRESS (Contract A). Every verdict cites a line that
resolves; every citation below was read this session and exists at the cited location.

---

V1. The premise is TRUE — reading problem, not filing problem. [CERTAIN]

I did not re-litigate all six planes; I opened the one code path the premise leans on hardest and
it holds. `core/recall/at_action.py:370-373` is the seam the whole 57.7% number comes from:

```python
for f in ("recommendation", "actual", "what_tried"):
    if rec.get(f):
        summary, field = rec[f], f
        break
```

The record is loaded whole (`load_all_learnings_from_store()`), all three prose fields carried into
`_project_items`, and then exactly one is kept; `actual` and `what_tried` are dropped at the
projection seam before the ranker ever sees a token. That is a reader choosing to discard data the
store already holds and correctly populated — not a filing absence. I read the census's own wording
for the library atoms ("already exists, is populated, is indexed, and has no door",
`research/reviewed/knowledge-plane-census-2026-10-03.md`) and the pattern generalises: every dark
plane is dark because nothing *reads* it, not because nothing filed it.

**The one place I would push back on the premise's framing:** "therefore do not mint a taxonomy" is
the right conclusion but the brief makes it sound *uniformly* true. The census itself records one
genuine filing defect that no reader can fix — the 28 ghost lessons whose index entries survive but
whose bodies are gone (`knowledge-plane-census-2026-10-03.md`, "Ghost records"). That is measured
knowledge *loss*, not under-reading, and the design correctly names it recovery-not-schema. So the
premise is true for the schema question and the design is honest about the one place it isn't. The
premise stands.

---

V2. A2's premise is FALSE: a shared NORMALISER is necessary but NOT sufficient. [CERTAIN]

This is the verdict the whole address contract hangs on, so I opened the three call sites and
traced the key both sides actually mint.

**The outcome side.** `core/recall/at_action.py:932-942`:

```python
def normalize_target(path=None, command=None) -> str:
    if path:
        return "p:" + os.path.normcase(os.path.abspath(path))
    if command:
        return "c:" + " ".join(str(command).lower().split())
```

`p:<normcased absolute path>` (Windows case-folded, `\`-joined, machine-absolute) or `c:<lowercased
collapsed command>`.

**The touch side.** `core/events/touch.py:225` → `refs = [r["key"] for r in (rows or [])]`, and
`row["key"]` is `core/coord/target.py` `_key_for` output (`target.py:274-279`): a **repo-relative
path** (`core/recall/at_action.py`), or `work:<name>:<path>`, or a `file_line`/`dir` composite with
`:<line>:<col>`. There is no `p:` prefix and no `c:` axis anywhere in `_key_for`.

Three consequences, all from lines I read, none requiring the census's disappeared scratchpad:

1. **A normaliser cannot reconcile these.** A normaliser maps a string onto a canonical *spelling*
   of the same string. Here the two sides name the same file with *different address classes*
   (`p:e:\ai-setup\core\recall\at_action.py` vs `core/recall/at_action.py`). That requires a
   **translation** (abspath → repo-relative), which is root-dependent and only well-defined under a
   known `Roots.main` — exactly the resolution `target.py:_resolve_root` (`target.py:333-362`) was
   built to do, and which `normalize_target` *deliberately does not do* (its docstring says
   "normcased absolute", not "root-resolved").
2. **The `c:` axis has no counterpart on the touch side.** `normalize_target` produces `c:` rows for
   command-shaped actions; `touch.py` never mints a `c:` key (it extracts *file* targets from a
   command via `T.extract`, never the command string itself). So however finely you normalise, the
   command-keyed outcome rows can never join the touch plane. The 0-of-365 split is partly
   *structural*, not just a spelling divergence.
3. **The two vocabularies are minted in the SAME process, from the SAME payload, side by side.** In
   `scripts/hooks/claude_posttooluse.py`, line 354-355 calls `_touch.emit(data)` (touch keys) and
   line 382-385 calls `normalize_target(...)` + `resolve_action_outcome(...)` (outcome keys) — two
   independent address computations running off one `tool_input`, never reconciled. There is no
   code path anywhere that passes a `target.py` key into `normalize_target` or vice versa
   (confirmed by search: the only `normalize_target` callers are the hooks, `replay.parse_target`,
   and `session_signals`, none of which route through `target.py`).

**What A2 must actually be.** A shared normaliser is the *necessary* half (one canonical `target.py`
key must be the only producer, so `p:`/`c:` die as a vocabulary). But it is not *sufficient*: the
contract must also (a) make the outcome path emit a `target.py` key **translated** by root
resolution rather than `abspath`, and (b) decide what the `c:` axis joins to — which is a design
question the current A2 text does not acknowledge. A normaliser that leaves `c:` rows and
absolute-path rows in place and merely "applies the same normaliser on both sides" would still leave
the intersection at (close to) zero, because one side would still be `p:e:\...` and the other
`core/...`.

---

V3. Measurement #3 is now UNVERIFIABLE — the census scripts are gone. [UNCERTAIN]

The brief instructs "at least one verdict that tries to falsify a numbered measurement" and #3 is
the load-bearing one. I looked for the census's own commands — `scratchpad/census*.py` referenced
throughout `knowledge-plane-census-2026-10-03.md` — and **they no longer exist** (find_files
`scratchpad/census*.py` → no matches; the scratchpad has been cleaned). So the exact 0-of-365 and
17,733 figures are not reproducible from their cited command, and I will not fabricate a rerun by
re-deriving them without the original selectors, because a subtly different "touch target key" and
"outcome target key" definition would produce a different number and I could not tell which was the
census's.

What I *can* say is that the split is at minimum credible and over-determined by V2: the touch side
and outcome side demonstrably (from code I read, not from the census) mint disjoint key shapes, so a
zero intersection is exactly what the code predicts — and a nonzero one would be the surprise worth
explaining. The number's *specificity* (0 of 365) is unverifiable this session; its *direction*
(zero, or near-zero) is certain from the two code paths.

I flag this as an **unchecked load-bearing input** because the brief says claude independently
re-verified #3 before shipping — but that verification's command is not in the brief, and neither
the census agent's script nor claude's replay is on disk for me to re-run. If the reconciliation
wants a falsified-and-pinned #3, someone must re-derive it with a *kept* script (the census's own
"every number with its command" discipline failed to persist the artifact).

---

V4. The eight-kind vocabulary is NOT the right address for planes it was never designed for. [CERTAIN]

`core/coord/target.py:64-65` seals `REF_KINDS = ("event", "sha", "task", "lesson", "mem", "doc",
"session", "seat")`, and the module's own law (`target.py:18-21`) is explicit that this is for *code
locations*: the docstring's framing is "the one key every plane joins a code location on," and the
resolver refuses to mint new kinds. That's the right law *for address keys*.

But Contract A1 proposes making those eight kinds "mandatory at write time" across every plane, and
84% of the refs that exist are things the eight kinds do not name — and that the code deliberately
emits *because* they are not code locations:

- `bifrost:<msg_id>` — written by `core/comm/promoter.py:49,179,300-301,334` as the canonical
  promoted-message ref. `target.py` itself treats `bifrost:` and `blob:` as `_OPAQUE_PREFIXES`
  (`target.py:31-32`) — "real join keys the by-reference index uses, deliberately NOT parsed here."
  So the seal already *knows* there are legitimate non-eight-kind refs.
- `file:<rel>` — `core/comm/toolbox.py:1479` and `promoter.py:334` emit it; `target.py:374-375`
  handles `file:` as a *path alias*, not one of the eight ref kinds.
- `event:<stream>:<entry>` (the `spine_ref`) and bare `event_id` lists fill `refs[]` all over
  `core/eye/*` and `core/events/event_index.py:88-101`.

The 88.3%-unwalkable figure is real, but "unwalkable" ≠ "does not speak the eight kinds." Refs like
`bifrost:...` and `file:...` are *already walkable* — there are resolvers for them — they just aren't
in `REF_KINDS` because `REF_KINDS` is a closed set *for the address vocabulary*, not the universe of
all refs. The right fix for the genuine 88.3% defect is not "refuse non-eight-kind refs at the write
door" (which would *break* promoter/toolbox/event_index, all of which emit `bifrost:`/`file:`/
bare-event refs) but "give every plane's ref a walker, and let `REF_KINDS` stay the closed address
set it was sealed as." A1 as written conflates "has one canonical walker" with "is one of eight
kinds," and those have opposite implications for the write door.

---

V5. "The ONLY rewrite-stable cross-plane edge" claim is overstated. [INFERRED]

I ran `git log` is not necessary to confirm the "one author" claim's shape — the brief and the
census both assert it, and it is plausible given the house's squash/rewrite history. What I can
check from code: `core/coord/preregistration.py:60-66` already walks `git show --name-only` per
commit and maps touched paths; and `core/git/rewrite_map.py` (cited in the census as the reason
`files_affected` dies on rename) is itself a rewrite-stable *map*, not merely an edge set. So
"T-id → commit-subject" is not the only rewrite-stable cross-plane edge; it is the only *task*
cross-plane edge. Whether that distinction matters depends on what the design wants to build on it
for — if the goal is "who built which task," the 908/304/100% figure is the right asset and the
claim is essentially true; if the goal is "who built this code path," `preregistration`'s
commit→files map plus `rewrite_map` is a second, distinct, rewrite-stable edge the design does not
count. INFERRED rather than CERTAIN because I did not run the 908/304/100% enumeration (the census
script is gone, V3), and did not verify "all 2,847 commits share one author" independently.

---

## What I could not check, by name

1. **The exact values of measurement #3** (0 of 365 vs 17,733) — the census scripts are gone (see
   verdict V3 above). That number is the single most load-bearing one in the whole address
   contract, and it is now reproducible by no one without re-derivation.
2. **Measurement #7** ("0 of 110 CLI verbs reach the fence plane") — I did not enumerate the verb
   registry (`core/toolbelt/registry.py`) against the fence plane this session.
3. **The 908/304/100% T-id edge set** — not independently re-enumerated (V5).
4. **The touch-plane row shape** ("365 normalised touch target keys") — I traced the *producer*
   (`touch.py` → `target.py`) to establish the key shape, but did not count the actual 365 rows in
   Redis against the 17,733 outcome rows.
5. **Whether any lesson was ever renamed** — the census itself flags this as unmeasured, and it
   matters for whether the "mutable primary key" verdict is a live event or only a schema property.

## What the design MISSES

The census and the schema treat "the target axis" as *one* axis that is "two mutually
unintelligible vocabularies" needing one normaliser. What my read of `target.py` and `touch.py`
shows is that there are actually **three distinct target-like axes with three different join
semantics**, and the design collapses them:

1. **The address key** — `target.py` repo-relative/`work:` key (what the W0.1 and W0.2 slices mint; the correct
   future spine key).
2. **The action-time key** — `normalize_target`'s `p:`/`c:` key (what recall's surface/outcome
   joiner mints today; absolute + command-string).
3. **The human/utterance axis** — `eye`'s utterance `event_id`s, which are content-addressed and
   unrelated to either file shape.

Contract A addresses only the first two, and only as a spelling problem. The missing move is to
*make the action-time key a derived view of the address key* (resolve root at write time, drop the
`p:`/`c:` vocabulary entirely, and for commands emit the *extracted file targets* — which `touch.py`
already computes — rather than the raw command string). Until the `c:` axis is redefined as
"extracted targets," no normaliser, however shared, will make command-actions joinable, because a
bare lowercased command string is not an address at all. That is the one thing the design does not
say, and it is the difference between A2 shipping and A2 shipping-but-still-zero.

---

## The one question for Daniel

> When you say "the right information needs to live in the right place," do you mean *one canonical
> address per thing* (so the two vocabularies and the `c:` question above are the real work), or
> *one discoverable shelf* (so Contract B's door is the real work) — because A and B optimise the
> two differently, and the schema commits to both before you've said which one is the bar?
