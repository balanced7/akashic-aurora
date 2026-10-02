# half-rill.md — one-spine — Rill (dsh_agent)

Blind. I read the brief and `core/comm/liveness.py` only; I did not open the other halves or the map/reconciliation inputs.

## ANSWER (my one question)

The one seam is `WorkLive.set()` at **`core/comm/liveness.py:146`** — the predicate `if phase != self._phase:`.

A phase *change* is observable there and ONLY there. `set()` is the one method that can tell a transition from a re-stamp, because it compares the incoming `phase` against the stored `self._phase`; `since_ts` moves only inside that branch (lines 147-148). The ~5 s heartbeat path is `refresh()` (line 154) → `_flush()` (line 158), which re-stamps `beat_ts` without touching `since_ts` and WITHOUT the phase comparison — so wiring Gap 2's emit into `_flush()` would fire every refresh (per-5 s), and wiring it into a reader (`read()` / `worklive_beat_age()`) would re-derive transitions from a refresh-shaped record and either miss fast transitions (idle → thinking → idle inside one 5 s window) or duplicate them.

**Wedge condition:** `phase != self._phase` — the incoming phase string differs from the stored `self._phase`. That is the exact predicate that makes `since_ts` move, and it is the predicate Gap 2's emit must be gated on.

## EVIDENCE (file:line, verbatim)

- `liveness.py:142-144` — `def set(self, phase: str, detail: str = "", new_turn: bool = False) -> None:` / "Record a phase transition (or a same-phase detail update). ``since_ts`` moves only when the phase actually changes, so time-in-phase is measurable across many beats."
- `liveness.py:146` — `if phase != self._phase:`
- `liveness.py:147-148` — `self._phase = str(phase)` / `self._since = time.time()`
- `liveness.py:154-156` — `def refresh(self) -> None:` / "Re-stamp the current phase (heartbeat thread). Keeps the key + TTL fresh; since_ts unchanged."
- `liveness.py:158` — `def _flush(self) -> None:` (the shared write that `set()` and `refresh()` both call; the per-5 s path)

## VERDICT ON THE FOLD (one spine)

HOLDS, scoped to Gap 2 (the gap my question owns). The phase-transition fact has a single, clean emit seam that maps directly onto the `capture_event(kind, summary, agent_id, session_id, detail, refs)` field model: a new `kind` (e.g. `phase`) emitted at `liveness.py:146` needs no new store, no new writer, and no narrative-schema change. That satisfies D1 ("the spine carries pointers, never bodies") and "no new store / no new writer."

I did not open the map or the Wave 0 table this session, so I state the fold for Gap 2 only and leave the four-gap/weld-order verdict to the reconciler and to the halves that read those inputs. A path I did not open is not evidence.

## WHAT I WOULD NOT BUILD

A polling reader that derives phase transitions from the worklive Redis key (`read()` / `worklive_beat_age()`), and an emit wired into `_flush()`. Both re-derive transitions from a refresh-shaped record: the first silently misses fast transitions, the second over-emits per beat. The transition must be emitted AT the transition (line 146), once, by the process that owns the phase — never inferred by a consumer.
