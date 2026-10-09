"""W3 -- the floor: a shadow-first, toggleable manifest of loud absence.

Spec: atom d622ac (H9), section 4 (Navi's floor-as-manifest). The floor is the INVERSION of normal
monitoring: not a ranked list of what matters, but the short list of conditions where SILENCE
ITSELF is the emergency -- "if you hear nothing here, something is already wrong." Four entries:
undeliverable directed mail, a guard that no-ops and reports success, a secret leaving the house,
and the floor going quiet itself.

Built the way Daniel asked (2026-10-08): TOGGLEABLE and SHADOW-FIRST, so we learn what works before
anything is allowed to interrupt. Three states per entry:

    off     -- not watching.
    shadow  -- watches and RECORDS what it would have done (a would-fire, journaled as a world-fact
               via core.oneworld.journal), but stays silent. The learning diary.
    live    -- actually surfaces as an alarm.

You run an entry in shadow, read its journaled diary (count/replay it with the projection -- the
would-fires are world-facts, so the calibration loop reuses W0/W0.1), and promote it to live only
once the diary says it would have been right. Nothing earns the right to interrupt you unproven.

MODES are named presets that set every entry's state at once (quiet / focus / night / firehose) --
switch the whole posture in one move. A mode cannot name an entry that does not exist.

THREE HONESTY RULES, each a scar:
- A sensor is THREE-state: fired / clear / UNAVAILABLE. "Quiet because I checked and it's fine" and
  "quiet because I'm blind here" are different observations, and the floor must never let the second
  read as the first -- a floor reporting all-clear while unwired is the exact 'guard reports success
  while doing nothing' it exists to catch (zero is not no; a guard that infers from context shares
  the failure it guards).
- Found-vs-taken CLOSES: every entry lands in exactly one bucket, and the engine writes the legend
  naming the tally -- the floor may not adjudicate its own silence (that would rebuild
  recall_adjudicates_its_own_silence one layer up).
- Every entry ships a FALSIFIER that must fire -- proof the entry CAN fire before it is trusted; a
  floor rule that cannot fire guards nothing, and one that cries wolf trains you to ignore it.

The default sensors are honestly UNWIRED -- a fresh floor reports all four as "unavailable, not
wired," never all-clear. Each real sensor (a roster x inbox scan, a guard-execution audit, an egress
detector, an external last-eval watchdog) is a small follow-on adapter named in the sensor's own
detail string; wiring each is safe to do incrementally because everything starts in shadow.
"""
from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional

from core.oneworld import journal

# Sensor verdict. THREE states, never collapsed to a boolean.
FIRED = "fired"
CLEAR = "clear"
UNAVAILABLE = "unavailable"

Signal = namedtuple("Signal", ["status", "detail"])

STATES = ("off", "shadow", "live")

_KEYS = ("undeliverable_mail", "noop_guard_success", "secret_egress", "floor_own_silence")


@dataclass
class FloorEntry:
    key: str
    state: str
    sensor: Callable[[], Signal]
    falsifier: Callable[[], Signal]
    description: str = ""
    budget_s: float = 0.0


def make_entry(key: str, sensor: Callable[[], Signal], *, state: str = "shadow",
               description: str = "", budget_s: float = 0.0,
               falsifier: Callable[[], Signal] = None) -> FloorEntry:
    """Build and validate one floor entry. state must be off/shadow/live. Default state is shadow
    (the learning gear). A missing falsifier defaults to one that fires -- but a real entry should
    carry a falsifier that constructs its OWN dangerous condition, so self_check proves it can fire."""
    if state not in STATES:
        raise ValueError(f"unknown state {state!r}; must be one of {STATES}")
    if falsifier is None:
        def falsifier():  # noqa: E306 -- a firing default so an entry is never un-falsifiable
            return Signal(FIRED, "falsifier: synthetic fire")
    return FloorEntry(key=str(key), state=state, sensor=sensor, falsifier=falsifier,
                      description=description, budget_s=float(budget_s))


def evaluate(entries: List[FloorEntry],
             previous: Optional[Dict[str, str]] = None,
             now: Optional[Callable[[], str]] = None) -> Dict[str, Any]:
    """Run each non-off entry's sensor and bucket the result, journaling fires as world-facts: a
    shadow fire is a `floor_would_fire` (the diary); a live fire is a `floor_fired` (a real alarm).
    Returns a report whose buckets account for EVERY entry, plus an engine-written legend, plus
    `statuses` ({key: fired|clear|unavailable|off}) for the next call to pass back as `previous`.

    `previous` makes the journal an EPISODE log: a fire is journaled only on the transition into
    fired, and its payload carries `since` (when that episode began), so fire -> clear -> fire is two
    facts. Without `previous` the W3 semantics hold: the journal is content-idempotent, so a steady
    identical fire is already one fact -- but a second episode with the same detail is invisible,
    which the floor's own calibration rule ("promote once the diary says it would have been right")
    cannot afford. Corrected 2026-10-09: I first assumed the journal would flood on every poll; the
    pins showed it is idempotent, and the real gap was uncountable episodes. Steady repeats are
    counted in `journal_suppressed`, never hidden.

    A sensor that raises is caught as UNAVAILABLE -- a sensor crashing means the floor cannot see
    that risk right now, which is a real (and honest) state, not a reason to take the floor down.
    """
    live_firing: List[dict] = []
    shadow_would_fire: List[dict] = []
    clear: List[dict] = []
    unavailable: List[dict] = []
    off: List[dict] = []
    diary_errors: List[str] = []
    statuses: Dict[str, str] = {}
    checked = suppressed = 0

    for e in entries:
        if e.state == "off":
            off.append({"key": e.key, "detail": "off"})
            statuses[e.key] = "off"
            continue
        checked += 1
        try:
            sig = e.sensor()
        except Exception as exc:  # noqa: BLE001 -- a crashed sensor is UNAVAILABLE, named, not fatal
            sig = Signal(UNAVAILABLE, f"sensor raised: {type(exc).__name__}: {exc}")
        rec = {"key": e.key, "detail": sig.detail}
        statuses[e.key] = sig.status if sig.status in (FIRED, CLEAR, UNAVAILABLE) else CLEAR
        if sig.status == FIRED:
            if e.state == "live":
                live_firing.append(rec)
                kind = "floor_fired"
            else:
                shadow_would_fire.append(rec)
                kind = "floor_would_fire"
            if previous is not None and previous.get(e.key) == FIRED:
                suppressed += 1  # the same steady fire as last time: already in the journal
                continue
            payload = {"entry": e.key, "status": sig.status, "detail": sig.detail}
            if previous is not None:  # episode mode: a new transition is a new fact
                payload["since"] = (now or journal._now_iso)()
            try:
                journal.append(kind, "floor", payload)
            except Exception as exc:  # the diary failing must be NAMED, never swallowed silently
                diary_errors.append(f"{e.key}: {type(exc).__name__}: {exc}")
        elif sig.status == UNAVAILABLE:
            unavailable.append(rec)
        else:
            clear.append(rec)

    total = len(entries)
    legend = (
        f"floor: {total} entr{'y' if total == 1 else 'ies'} ({len(off)} off); "
        f"checked {checked}; {len(live_firing)} FIRING, "
        f"{len(shadow_would_fire)} would-fire (shadow), {len(clear)} clear, "
        f"{len(unavailable)} unavailable (cannot see)"
        + (f"; {len(diary_errors)} diary write error(s)" if diary_errors else "")
    )
    return {
        "live_firing": live_firing, "shadow_would_fire": shadow_would_fire,
        "clear": clear, "unavailable": unavailable, "off": off,
        "checked": checked, "total": total, "diary_errors": diary_errors, "legend": legend,
        "statuses": statuses, "journal_suppressed": suppressed,
    }


def self_check(entries: List[FloorEntry]) -> Dict[str, bool]:
    """Run every entry's falsifier and confirm it FIRES. A False here means an entry that cannot
    fire -- it guards nothing and must not be trusted until its falsifier is fixed."""
    out: Dict[str, bool] = {}
    for e in entries:
        try:
            out[e.key] = (e.falsifier().status == FIRED)
        except Exception:  # noqa: BLE001
            out[e.key] = False
    return out


# ------------------------------------------------------------------ the four entries

def _unwired(msg: str) -> Callable[[], Signal]:
    return lambda: Signal(UNAVAILABLE, msg)


def _falsify(msg: str) -> Callable[[], Signal]:
    return lambda: Signal(FIRED, msg)


def default_manifest() -> List[FloorEntry]:
    """The four entries, ALL in shadow (shadow-first), with honestly-unwired sensors. Each sensor's
    detail names the real adapter that would wire it (UNWIRE-WHEN); each falsifier constructs the
    entry's own dangerous condition so self_check proves the entry can fire."""
    from core.oneworld import sensors  # imported here: sensors imports this module's Signal and states
    return [
        make_entry(
            "undeliverable_mail",
            # Wired 2026-10-09 (core/oneworld/sensors.py): roster x shadow mailbox. The lambdas look the sensor up
            # at call time, so a patched or reloaded sensors module is the one that runs.
            sensor=lambda: sensors.undeliverable_mail(),
            falsifier=lambda: sensors.undeliverable_mail_falsifier(),
            description="mail to a specific agent that cannot be delivered -- more urgent than a "
                        "backlog, because it never arrives unless someone notices"),
        make_entry(
            "noop_guard_success",
            sensor=_unwired("not wired: needs a guard-execution audit "
                            "(fail-open / swallowed-exception detector)"),
            falsifier=_falsify("falsifier: a guard that returned OK while its body raised and was "
                               "swallowed"),
            description="a safety check that did nothing and reported success -- broken in a way "
                        "that looks exactly like working"),
        make_entry(
            "secret_egress",
            sensor=_unwired("not wired: needs an outbound egress detector; blast radius is OUTSIDE "
                            "the house, so this is the one worth a force-dump"),
            falsifier=_falsify("falsifier: a credential-shaped string crossing an outbound boundary"),
            description="a secret leaving the house"),
        make_entry(
            "floor_own_silence",
            sensor=_unwired("not wired: needs an EXTERNAL watchdog reading the floor's last-eval "
                            "stamp -- the floor cannot detect its own stop from inside"),
            falsifier=_falsify("falsifier: last floor eval older than its budget"),
            description="the floor itself going quiet -- a dead floor and a calm floor look "
                        "identical unless the floor is made to prove it is alive",
            budget_s=300.0),
    ]


# ------------------------------------------------------------------ modes (named presets)

MODES: Dict[str, Dict[str, str]] = {
    # nothing speaks; everything watches -- the safe default for a new floor or a quiet night.
    "night": {k: "shadow" for k in _KEYS},
    # everything live and loud.
    "firehose": {k: "live" for k in _KEYS},
    # the two whose silence hurts most are live; the rest keep watching.
    "focus": {"secret_egress": "live", "undeliverable_mail": "live",
              "noop_guard_success": "shadow", "floor_own_silence": "shadow"},
    # near-silent, but a secret leak still fires even here -- its blast radius is outside the house.
    "quiet": {"secret_egress": "live", "undeliverable_mail": "off",
              "noop_guard_success": "off", "floor_own_silence": "off"},
}


def apply_mode(entries: List[FloorEntry], name: str) -> List[FloorEntry]:
    """Return a copy of `entries` with each state set by the named mode. A mode leaves an entry it
    does not name at its current state. Refuses an unknown mode."""
    if name not in MODES:
        raise ValueError(f"unknown mode {name!r}; known modes: {sorted(MODES)}")
    mode = MODES[name]
    return [replace(e, state=mode.get(e.key, e.state)) for e in entries]
