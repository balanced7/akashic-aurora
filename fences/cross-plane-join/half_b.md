V1. The cross-plane-join arc is the most-designed, least-built arc in this house: four reconciled designs, seven approved ledger rows with no code, one ratified door never wired, five partial organs. The question the evidence actually poses is not "how do we build the join" but "why does this arc never get built, and what is the smallest thing that breaks that pattern." [CERTAIN]
V2. The connectome holds ZERO edges. The typed edge graph does not exist. `fence` and `recall-firing` are vocabulary with no producer. The live `edges` table in `state/eye/eye.db` has 0 rows, `eye trace` exits 2 at the empty-connectome guard (`agent_cli.py:2717-2720`), and a full rebuild yields 36,876 edges with 0 of the five mind-formed kinds. [CERTAIN]
V3. `session_id` is 0.82% filled (165 of 20,208 events over the uncapped union), not 0.0%. The conclusion survives: exactly 1 of 49 kinds carries it, and the share fell in the most recent month. But the count is the correction. [CERTAIN]
V4. The smallest thing that breaks the never-built pattern is a single wired door: `agent_cli.py arc <id>` calling `scripts/arc_thread.py`. It is the only artifact in the arc that is already built, already tested, and already documented in `docs/LIBRARY.md:61`, yet unreachable from any production entry point. Wiring it is the smallest possible proof that this house can finish a join-arc slice. [DESIGN]
V5. A fifth reconciled design is the wrong answer. The evidence says it joins the other four. The right answer is a build-order that starts with the smallest wired door and uses it to measure whether the next slice should exist. [DESIGN]

---

## 1. VERDICT ON THE FRAMING

The brief asked the right question and then answered it in the wrong tense.

Daniel asked: *"how do we further reinforce it in a reliable and performant way so we increase the indexable surface area of our tools."* The brief's evidence pack measured the surface area and found it broken. Annex B measured it again and found it broken in more places, with better numbers. Both packs are correct. Both are also answering the question as if the problem is a design gap.

It is not. The evidence now shows a **completion gap**.

The arc has been designed four times. It has been ratified, parked, re-opened, and re-ratified. The `arc <id>` door exists as a standalone script with tests (`scripts/arc_thread.py`, `tests/test_arc_thread.py`) and is named in `docs/LIBRARY.md:61` as door 2 of the library. It is not wired into `agent_cli.py`. The connectome has a vocabulary for eight edge kinds; five have no writer. The event plane has a `session_id` parameter; 3 of 121 call sites pass it. The `LIBRARY.md` door 2 is documented; it is unreachable.

The brief's §3.9 said the annex would be additive and would not overturn anything. That was wrong. The annex overturned the two most load-bearing claims in §3.1 and §3.3, and it reframed the question. The question is no longer "what should we build." It is **"why does this arc never get built, and what is the smallest thing that breaks that pattern."**

I state that as my framing verdict, and it outranks everything else in this document.

## 2. THE DESIGN

### 2.1 The smallest thing that breaks the pattern

**Wire `scripts/arc_thread.py` into `agent_cli.py` as `agent_cli.py arc <id>`.**

That is the entire design. It is the smallest possible artifact that:
- is already built and tested;
- is already documented as a door in the ratified library schema;
- is already the exact triangulation Daniel asked for ("trace our steps, materialized");
- and is currently unreachable from any production entry point.

Wiring it is not a new design. It is the completion of an existing one. It costs one import, one subparser registration, and one line in `cmd_arc` that delegates to `arc_thread.main`. It is reversible. It is measurable. And it is the smallest possible proof that this house can finish a join-arc slice.

### 2.2 What to change, what to leave alone

**Change:**
- `agent_cli.py`: add `arc` subparser, delegate to `scripts/arc_thread.py`.
- `docs/DOORS.md`: add the `arc` verb to the door manifest (if it is not already there; I did not check).

**Leave alone:**
- The connectome. It is not a cross-plane graph. Do not bend it.
- The event plane's `session_id` parameter. It is a door signature, not a bug. The 0.82% fill is honest: it means "no session in scope" for the 99.18% and "session in scope" for the 0.82%. Do not backfill. Do not guess.
- The `refs` vocabulary. The untyped 281 are Redis stream ids; the typed `bifrost:` prefix exists. Normalizing them is a separate slice, not this one.

### 2.3 The second slice, conditional on the first

If the `arc` door is wired and used, the second slice is the `session_id` write-side fix. Not because it is the next most important, but because it is the next most measurable. The annex measured 121 call sites, 3 passing `session_id`. The fix is a single ambient default in `event_log.py` reading `BIFROST_INCARNATION` or `CLAUDE_CODE_SESSION_ID`. It is the same shape as the `arc` wiring: one line, reversible, measurable.

But it is conditional. If the `arc` door is wired and not used, the problem is not the door. It is the demand. And the next slice should be a demand-side measurement, not another write-side fix.

## 3. ORDERING, WITH THE REASON

1. **Wire `arc <id>` first.** It is the only artifact that is already built, already tested, already documented, and already the exact thing Daniel asked for. It is the smallest possible proof that this house can finish a join-arc slice. Every other slice is either unbuilt (connectome writers, session_id ambient default) or unmeasured (demand for the `arc` door).

2. **Measure usage.** The `arc` door must emit a `command` event with `detail.arc` and `detail.duration_ms`. If it is used, the second slice is justified. If it is not, the problem is demand, not supply, and the next slice is a demand-side instrument, not another write-side fix.

3. **The `session_id` ambient default is conditional on (2).** It is the next most measurable write-side fix, but it is not the next most important. The connectome writers are more important and less measurable. The `session_id` default is the next most measurable because it has a single falsifier: after the default lands, the fill rate must rise above 0.82% within one session.

The dependency to state explicitly: **(1) is a precondition for (2), and (2) is a precondition for (3).** If (1) is wired and (2) shows no usage, (3) is a waste. The house has already built four designs that were not used. Do not build a fifth.

## 4. WHAT I WOULD NOT BUILD, AND WHY

**A fifth reconciled design.** The evidence says it joins the other four. The house does not need another design. It needs a completion.

**A cross-plane edge table.** The connectome is utterance-scoped. A cross-plane table would be a regenerable projection masquerading as durable history, and it would immediately re-ask every question the authorship ledger already answered once about surviving rewrites.

**A `session_id` backfill of history.** The 0.82% fill is honest. Old events keep `""` and read as "pre-fix." Guessing session ids from timestamps launders an inference as a record.

**Normalizing the 281 untyped refs into `bifrost:`.** The forked-spelling problem is real, but it is a separate slice. It is not the smallest thing that breaks the pattern.

**Any new door.** The `arc` door exists. Wire it. Do not build another.

## 5. THE CHEAPEST EXPERIMENT THAT WOULD FALSIFY MY OWN DESIGN

One command, run after the `arc` door is wired:

```
py agent_cli.py arc cross-plane-join --json | py -c "import json,sys; d=json.load(sys.stdin); print('items:', len(d.get('items', []))); print('commits:', len([i for i in d.get('items', []) if i.get('type') == 'commit']))"
```

If this prints `items: 0` or `commits: 0`, then `arc_thread.py` is not reading the records it claims to read, and the design collapses to "the door is wired but the substrate is empty," which is a different defect (and a more embarrassing one). If it prints a non-zero number, the door works and the design is falsified only if usage is zero after one week.

The secondary falsifier: `py agent_cli.py events --kind command --limit 100 --json | py -c "import json,sys; r=json.load(sys.stdin); print(sum(1 for x in r if 'arc' in (x.get('summary') or '').lower()), 'arc commands in last 100')"`. If this prints 0 after one week, the door is wired but unused, and the problem is demand, not supply.

## 6. COST

- **Per-write**: zero. The `arc` door is read-only.
- **Per-read**: O(arc items). `arc_thread.py` reads the header plane (`Arc:` fields) and the git log. It does not scan the corpus. It is bounded by the number of items in one arc, which is small.
- **Storage growth**: zero. The door is a view over existing records.
- **At 10x corpus**: the header plane is already indexed by `Arc:` field. The git log is already indexed by commit. The door scales linearly with the number of items in one arc, not with the corpus.

## 7. WHAT I COULD NOT CHECK

- **Whether `arc_thread.py` is already wired in a worktree or a sibling's branch.** I searched `agent_cli.py` in the main tree and found no `cmd_arc` or `arc_thread` import. I did not search every worktree. If it is already wired elsewhere, this half is redundant.
- **Whether the `arc` door's output format is the right one for the reconciler.** I did not read `arc_thread.py` in detail. I verified it exists, it is tested, and it is documented in `docs/LIBRARY.md:61`. The output format is a detail the reconciler can adjust.
- **Whether the `session_id` ambient default would break any test that passes `session_id=""` explicitly.** The annex found 3 production sites and many tests. The default must be opt-out, not opt-in, and the tests that rely on `""` must be pinned. I did not audit the tests.
- **Whether the connectome's zero edges are a defect or a feature.** The annex says the schema-6 migration dropped the edges and no `eye ingest` followed. I did not verify the migration. The zero edges are a fact; whether they are a defect is a ruling I am not positioned to make.

---

### Annex note

Annex B landed before I sealed. It overturned two claims I would otherwise have inherited from the brief (§3.1 the connectome exists, §3.3 session_id is 0.0%). I verified the corrections myself by reading the code and the records. The corrections stand. The framing verdict is mine.
