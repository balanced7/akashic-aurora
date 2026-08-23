"""wedge_discriminator (T376 S5) -- the wedged-vs-thinking decision rule.

The reconciled design adopted half_a §2 VERBATIM as the wedged arm's spec:
the tiebreaker between "wedged" and "thinking" is the THREAD STACK, never the
timeout alone. This module is that spec as a pure function the doctor/OOB
path can call instead of telling a human to run py-spy by hand.

THE LAW (one sentence, half_a §2 head): wedged and thinking diverge on four
planes, and the tiebreaker -- the only plane that cleanly separates them --
is the thread stack, not any timeout.

The decision rule (half_a §2.3):

    WEDGED        iff aged non-idle phase + dead pulse AND the MainThread is
                  blocked in a write/flush/socket-recv (streams.py / the
                  _stream_turn family) -- stuck doing I/O that is not a model
                  call and not a producer-consumer wait. kill/relaunch on the
                  table.
    THINKING      iff the MainThread is above the model call, or idle in a
                  _process_one / producer-consumer wait with a live beat --
                  regardless of how long the phase has aged.
    INSTRUMENT-FAULT iff beat fresh + pulse "dead" but the stack shows a
                  healthy wait -- the two liveness organs disagree; fix the
                  organ, not the worker.

FAIL DIRECTION IS THINKING (half_a §2.4): a false WEDGED (kill a thinker)
costs a turn + warm cache + RB-26 redelivery + destroying a healthy runner;
a false THINKING (let a wedge sit) costs what today already cost and
self-heals. So the stack is REQUIRED before a kill: absent or garbled stack
evidence resolves to THINKING, never WEDGED.

SCOPE (half_a §2.5): py-spy reaches Python-runner MainThreads (the
bifrost_runner_*.py family). A Claude Code harness seat can only be replaced
(mark-dead + reroute), never recovered, so it needs no discrimination -- this
rule is for polling runners only, where py-spy is free and proven.

No new thresholds -- the floor imports the existing liveness.DEFAULT_WEDGE_S
(300s, env BIFROST_WEDGE_SECONDS); everything else is a passed input from the
signals the doctor already computes (phase age, pulse age, beat age).
"""
from __future__ import annotations

from typing import Optional

# The thread-stack signatures that NAME the disease. These are meaning, not
# membership: a stack "blocked in a write/flush/socket-recv" is the T019
# undrained-output family (the deepseek receipt, streams.py write+flush);
# a stack "above the model call or idle in a worker wait" is the healthy
# family (the kimi receipt, _process_one wait). Classifying by MEANING, not by
# a hand-written list of frames, is what keeps this from drifting the moment a
# module moves (the convergent_fixes_describe_meaning_not_location lesson).

# Frames that say "this thread is writing its own output and stuck" -- the
# T019 pipe family. Written as substrings the stack text will contain when the
# MainThread is genuinely wedged on undrained I/O.
_BLOCKED_IO_MARKERS = (
    "streams.py",            # core/foundation/streams.py write/flush
    "_stream_turn",          # the runner's stream-flush path
    "flush",                 # a flush call in the stack
    "socket.py",             # raw socket recv/sendall
    ".recv(",                # blocked read on a socket
    "sendall",               # blocked write on a socket
)

# Frames that say "this thread is waiting on work, not stuck" -- a clean
# producer-consumer / worker wait. A live beat PLUS these is the healthy kimi
# receipt, not a wedge.
_HEALTHY_WAIT_MARKERS = (
    "_process_one",          # the runner's per-message worker loop
    "threading",             # threading.Event.wait / Condition.wait
    ".wait(",                # any explicit wait primitive
    "chan.receive",          # channel recv (producer-consumer)
)

# Frames that say "this thread is inside a model call" -- thinking, not wedged.
_MODEL_CALL_MARKERS = (
    ".create(",              # openai-style client .create / completions
    "chat.py",               # the seat's chat module above the client
    "_completion",           # a completion entry point
    "openai/",
    "responses",
)


def _has(stack: str, markers: tuple) -> bool:
    """True if any marker substring appears in the stack text (meaning, not
    exact frame match -- the stack can carry absolute paths or shortened
    module names)."""
    return any(m in stack for m in markers)


def classify(stack: Optional[str], *, phase_age_s: Optional[float],
             pulse_age_s: Optional[float],
             beat_age_s: Optional[float],
             wedge_floor_s: Optional[float] = None) -> str:
    """Classify a runner's state as 'wedged' | 'thinking' | 'instrument_fault'.

    `stack` is the py-spy dump text (may be None/empty -- that means no stack
    evidence, which by fail-direction is THINKING). `phase_age_s` / `pulse_age_s`
    / `beat_age_s` are the liveness signals the doctor already computes.
    `wedge_floor_s` defaults to the existing liveness.DEFAULT_WEDGE_S (never a
    new constant).

    Fail direction is THINKING everywhere: unknown numbers, absent stack, and
    absent positive evidence of a blocked write all resolve away from a kill.
    """
    try:
        from core.comm import liveness
        floor = float(wedge_floor_s) if wedge_floor_s is not None \
            else float(getattr(liveness, "DEFAULT_WEDGE_S", 300.0))
    except Exception:
        floor = float(wedge_floor_s) if wedge_floor_s is not None else 300.0

    # Unknown numbers -> fail toward thinking (never kill on missing evidence).
    if phase_age_s is None or pulse_age_s is None or beat_age_s is None:
        return "thinking"
    phase_age = float(phase_age_s)
    pulse_age = float(pulse_age_s)
    beat_age = float(beat_age_s)

    # Absent/garbled stack -> THINKING (fail-direction, the core of P4). A
    # kill is only ever on positive evidence of a blocked write.
    if not stack or not isinstance(stack, str):
        return "thinking"
    lowered = stack.lower()

    # The two "healthy wait + live beat" shapes split on the PHASE AGE, and the
    # spec's own words draw the line:
    #   INSTRUMENT-FAULT (half_a §2.3) = beat fresh + pulse dead + healthy wait,
    #       "the two liveness organs disagree" -- the EARLY form, diagnosed
    #       BEFORE the phase ages into the wedge window: fix the organ, not the
    #       worker, and the wedge never pages.
    #   THINKING (half_a §2.3) = idle in a _process_one / producer-consumer wait
    #       with a live beat "REGARDLESS of how long the phase has aged" -- the
    #       kimi receipt AS THE WEDGE WINDOW CLOSES: age alone is not a wedge,
    #       so it resolves away from a kill.
    # Precedence: instrument-fault is the SUB-floor form (phase not yet aged);
    # once the phase is at/over the floor, the same signature is plain thinking
    # (never a kill). Blocked I/O always wins over both -- that is the wedge.
    beat_fresh = beat_age <= 60.0          # fresh enough to read as alive
    pulse_dead = pulse_age >= 10.0         # older than ~2x PROGRESS_TTL (5s)
    healthy_wait = _has(lowered, _HEALTHY_WAIT_MARKERS)
    blocked_io = _has(lowered, _BLOCKED_IO_MARKERS)

    if not blocked_io and healthy_wait and beat_fresh and pulse_dead \
            and phase_age < floor:
        return "instrument_fault"

    # WEDGED: the full AND chain from §2.3 -- aged non-idle phase, dead pulse,
    # AND positive evidence the MainThread is blocked writing its own output.
    aged_phase = phase_age >= floor
    if aged_phase and pulse_dead and blocked_io:
        return "wedged"

    # THINKING: the default -- above the model call, idle in a wait with a
    # live beat, or simply not proven wedged. This is the cheap side and it
    # self-heals.
    return "thinking"
