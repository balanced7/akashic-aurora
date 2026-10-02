# one-spine · half_a · Heimdall (deepseek)

Fence: one-spine · Slot: half_a · Seat: Heimdall · Blind to half_b / half-rill / half-sol
Read only: the brief's INPUTS (the map, reconciliation lines 118-150, navi-m1, T424 slice,
event_log.py, liveness.py, roster.py, resume_on_deaf.py, wire_journal.py, this morning's receipt).

---

## ANSWER (the one question)

**W0.2 already closes Gap 3 fully — and it does so by construction, not by addition.**

The brief's W0.2 table (reconciliation `# 4. Wave 0`, the touch row) is:

> `capture(kind="touch", refs=[typed], session_id=, detail={schema: "touch.v1", harness, tool,
> action, targets, ...})` … **`session_id forwarded on every capture_event in the hook path`** …
> fail-open with a drop counter; nothing raw stored.

Read against Gap 3 in the map (`the-record-is-total-map-2026-10-01.md`, THE FOUR GAPS):

> GAP 3 — ACTIVITY. `touch_activity` writes a temp-dir `.alive` stamp. It is a fact ("a hook
> fired") with no spine record. ROUTE: keep the `.alive` file … but ALSO emit `kind='activity'`
> … **one emit per turn-idle → active transition is enough**.

Gap 3's route is: keep the `.alive` stamp (cheap fast-path the janitor reads) AND emit one
spine event per turn-idle→active transition. W0.2 is exactly that, with a strictly better emit:

- The **`.alive` stamp already survives** in the W0.2 spec — `touch_activity` is not touched by
  the touch emit; the janitor's fast-path (`resume_on_deaf.py` / `wake_seat` reads `activity_age_min`)
  keeps working identically.
- The **transition spine event is already delivered** — the `touch` emit is *emitted from the
  hook path*, which is precisely the turn-idle→active transition. A hook fire *is* the transition.
  There is no earlier moment than the hook path to observe the transition, and the hook path is
  where W0.2 puts the emit.
- The **throttle is already decided** — W0.2 emits once per hook (per touch), which is coarser
  than per-hook-*command* if a turn multi-touches, and identical to Gap 3's "one emit per
  transition" in the single-touch-per-turn case. The one remaining knob the map left open (Q1:
  per-turn-transition vs minimum-interval) is answered *by the W0.2 shape itself*: a touch fire
  is the transition, so "once per touch" **is** "once per transition." No separate `kind='activity'`
  emit is needed — Gap 3 does not want its own kind; it wants the transition to land on the spine,
  and the touch emit is that landing.

**What W0.2 must add to close Gap 3 fully: nothing, in the emit itself.** The two requirements
that are *preconditions*, not additions, are already in the W0.2 row:

1. **`session_id` forwarded on every capture_event in the hook path** — already specced. `event_log.py:318`
   `capture_event(kind, summary, **kwargs)` and `event_log.py:109` `capture(..., session_id: str = "")`
   already accept it as a first-class field (`event_log.py:142` cleans it into the record). The only
   thing to verify in the W0.2 build is that the hook-passed `session_id` actually reaches the
   singleton's `capture` call — that's a wiring check, not a schema change. This is the single
   field that makes a touch a *seat-and-session* fact (a hook fired *in this incarnation*) rather
   than a bare "something touched something," which is why the brief lists it in the same breath.
2. **Fail-open with a drop counter** — already specced. The W0.2 touch path must not wedge the
   host command; `capture_event` at `event_log.py:319-325` already swallows every Exception and
   returns a `BoundaryOutcome`. The "drop counter" is the one W0.2-specific addition to *share*
   the fail-open guarantee with the map's "fail-open-with-counted-drops" doctrine, and it belongs
   in the Wave-0 instrument (W0.4 `context --stats` already reads a drop counter), not in Gap 3.

The fold: **Gap 3 is not a gap that needs its own emit. It is the transition that the W0.2 touch
emit already, and only, lands on the spine.** Where Gap 1 (wire: each record → `kind='wire'`),
Gap 2 (worklive: phase change → `kind='phase'`/`'beat'`/`'wedge'`), and Gap 4 (janitor:
declare/retract/revoke → three kinds) each need a *new* emit with a *new* `kind`, Gap 3 has no
distinct fact beyond "a hook fired," and "a hook fired" *is* the touch. It absorbs not by adding
a fourth emit but by the W0.2 emit being the activity transition in its most spine-native spelling.

**Does my weld order change once Gap 3 is W0.2? Yes — collapse the last two, and hold the result.**

My map proposed `2 → 4 → 1 → 3` (worklive, expected/retract/revoke, wire, activity-last). With
Gap 3 folding into W0.2 (which is itself Wave-0 slice #2, already ahead of every weld), the
activity emit no longer has an independent slot. The new order:

   1. **Gap 2 (worklive phase/wedge)** — unchanged; highest signal per byte, hooks already at the work path.
   2. **Gap 4 (expected/retract/revoke)** — unchanged; closes the earlier janitor ruling *and* lands on the spine in one move.
   3. **Gap 1 (wire)** — unchanged; one line per wire record, bodies out per D1.
   4. **Gap 3 (activity)** — *demoted on purpose*: its transition-fact is carried by W0.2's touch emit,
      so there is no separate weld to schedule. Assert the flip (a hook firing == a touch == the
      idle→active transition) as the W0.2 acceptance, and Gap 3 is *closed when W0.2 lands*, not
      after three other welds.

The order does not *change* so much as *shorten*; the four-gap weld becomes a three-gap weld plus
a W0.2 assertion. That is the whole point of "W0.2 is Gap 3 done properly" in the brief's intent,
and I now see it is true — W0.2 is not merely a better Gap 3, it is Gap 3 with the emit already
live at the earliest possible observer (the hook), so welding it *separately later* would be
re-emiting the same fact a second time as a different `kind`. Two kinds for one transition is the
rival-assembler smell both documents warn against; the fold is the fix, and it is the W0.2 emit.

**What I would not build:** a distinct `kind='activity'` emit on top of W0.2. That would place the
same observable (a hook fired) on the spine twice, under two kinds, one from the hook path (touch)
and one from a later activity slice (activity) — a second writer for one fact. D1/D2 and the map's
"no new writer, no new store" both forbid it. The `.alive` stamp stays (it is a *state* a janitor
polls, not an event to replay); the *event* of the transition is the touch, once.

---

## FIRST `kind` FROM `liveness.py` — and the exact line

**`kind='phase'`**, emitted from inside the `set()` phase-change gate, `core/comm/liveness.py:146` —

> ```python
> with self._lock:
>     if phase != self._phase:          # <- line 146, core/comm/liveness.py
>         self._phase = str(phase)
>         self._since = time.time()
> ```

The emit goes **inside that `if`, after `self._since = time.time()`** (i.e. after line 148, before
the `self._detail = ...` line). It must *not* go in `_flush()` (line 154) and *must not* go in
`refresh()` (line 151) — `_flush()` is called by every `refresh()` on the ~5s heartbeat, and the
map's Gap 2 route is explicit: "not every 5s refresh — that's spam." Placing it inside the
`phase != self._phase` gate is the *one* seam where a transition is observable, and it fires
exactly once per transition, never per 5s refresh, never per same-phase `set()`.

The emit, expressed against the existing `capture_event` one-liner (`event_log.py:318`):

> `capture_event("phase", f"{self.agent}: {old_phase} -> {self._phase}", agent_id=self.agent,
> session_id=<the session id forwarded from the caller>, detail={"phase": self._phase,
> "since_ts": self._since, "turn": self._turn, "code_sha": _safe_code_sha()})`

Two notes on that emit, both load-bearing:

1. **`session_id` is the one field W0.2 makes the emit carry that liveness does not yet have in
   scope.** `WorkLive.__init__(self, agent)` holds `self.agent` (line 132) but no session id. The
   W0.2 "session id forwarded on every capture_event in the hook path" is what makes this a
   *seat-and-incarnation* fact rather than a bare agent fact — which is exactly the fix this
   morning's receipt demanded (the ear read a private file on a stale worktree and fired a
   cold-seat notice at a live, armed Vandor, because "which Vandor, in which session" was not a
   spine fact). `set()` already takes `detail`; adding a `session_id` (or reading it from the
   forwarded hook context) is the whole W0.2 join. Without it, `kind='phase'` collapses two
   incarnations of one agent into one spine story — the failure `live_incarnations()` was built to
   name, not hide.
2. **`_safe_code_sha()` is already the wedge-fact.** `liveness.py:36-68` caches `code_sha` once
   per process (because a process's code cannot change under it). The `kind='phase'` emit carrying
   `code_sha` is what makes "a fix was shipped, announced, and believed while no process runs it"
   (the T114 story in the docstring) a *replayable spine fact* instead of a TTL'd key that
   evaporates. The `kind='wedge'` emit (the map's other Gap-2 kind) belongs in the watchdog that
   *reads* `since_ts` ageing, not in `set()` — `set()` never observes a wedge (a wedge is the
   *absence* of a `set()`, which only an external reader can see). So the first kind out of
   `liveness.py` is `phase`, and `wedge` is a *separate* emit in the reader (L2 watchdog /
   supervisor), never in the beater.

**Exact line, one more time, for the pin:** `core/comm/liveness.py:146`, the `if phase != self._phase:`
line — the emit is inserted into the body of that branch.

---

## EVIDENCE (file:line, verbatim)

- `core/comm/liveness.py:146` — `if phase != self._phase:` (the phase-change gate).
- `core/comm/liveness.py:151-152` — `def refresh(self)` → `self._flush()` (the 5s path; must NOT emit).
- `core/comm/liveness.py:154` — `def _flush(self)` (shared by `set()` and `refresh()`; must NOT emit).
- `core/comm/liveness.py:132` — `self.agent = str(agent)` (agent in scope; session id is NOT yet here → the W0.2 forwarding join).
- `core/comm/liveness.py:36-68` — `_running_code_sha()` / `_safe_code_sha()` (the T114 wedge fact, cached once).
- `core/events/event_log.py:109` — `session_id: str = ""` (first-class field on `capture`).
- `core/events/event_log.py:142` — `"session_id": self._clean(session_id)` (cleaned into the record).
- `core/events/event_log.py:318` — `def capture_event(kind, summary, **kwargs)` (the hot-path one-liner).
- `core/events/event_log.py:319-325` — the one-liner swallows every Exception and returns `BoundaryOutcome` (the fail-open the W0.2 drop counter rides).
- The map (`the-record-is-total-map-2026-10-01.md`): Gap 2 route "on PHASE CHANGE … emit kind='beat'/'phase'/'wedge' … not every 5s refresh"; Gap 3 route "keep the .alive file … but ALSO emit kind='activity' … one emit per turn-idle → active transition"; weld order `2-4-1-3`.
- The brief's W0.2 row (`fences/context-system/reconciliation.md`, Wave 0 table): `session_id forwarded on every capture_event in the hook path`; `fail-open with a drop counter`.
- `resume_on_deaf.py:34` `declare_expected` / `:71` `retract_expected` (Gap 4 facts, today private-file-only → `kind='expected'` / `'retract'` / `'revoke'`).

---

## VERDICT ON THE FOLD

**HOLDS.** The four gaps and Wave 0 are one spine with one weld order, and the fold is genuine,
not a relabel: Gap 3 has no distinct fact beyond "a hook fired," and "a hook fired" *is* the W0.2
touch. The three welds with distinct facts (wire → `kind='wire'`, worklive → `kind='phase'`, janitor
→ `kind='expected'/'retract'/'revoke'`) remain, and the fourth (activity) is absorbed by W0.2's
touch emit, the same transition from the earliest possible observer. The weld order shortens from
four slices to three-plus-one-assertion; nothing about the map's scope discipline (no new writer,
no new store, pointers-not-bodies) moves.

---

## WHAT I WOULD NOT BUILD

1. A distinct `kind='activity'` emit beside the W0.2 touch — one fact (a hook fired) on the spine
   twice, under two kinds, is a second writer for one transition.
2. The `kind='phase'` emit in `_flush()` or `refresh()` — that turns a ~5s heartbeat into a
   per-second firehose, the exact spam the map's Gap 2 route forbids.
3. A `kind='wedge'` emit from `liveness.py` — this module only *observes*; a wedge is the absence
   of a `set()`, observable only by the reader (watchdog/supervisor), never by the beater that
   never runs while wedged.
