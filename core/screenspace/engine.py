"""Screenspace engine facade — digest verdicts (T386 §1, §2, §3, §4).

This is the FACADE altitude of the observe organ, above the ``capture``
substrate. Where ``capture.screen`` returns raw pixels + physical truth
(``ScreenFrame``), the verbs here return *digest verdicts* — the §2 ladder's
content, shaped so a caller can decide whether to climb to a higher level.

Verbs (observe-only, §6 step 2):
  peek(level, scope=None, budget=None) -> ScreenResult
  delta(since_gen)                     -> ScreenDelta
  refs(scope)                          -> list[Ref]
  read_text(scope, method="uia"|"ocr") -> TextResult

NOT here (step 3+, gated on step 0): locate, act, input, watch. Their presences
in the RED pins (BAR_OBSERVE_LOCATE_ACT_MS, BAR_INPUT_DISPATCH_MS) are
registered-not-built constants only — this module deliberately does not implement
them.

ScreenResult carries the §2 verdict fields verbatim (window / focus / gen /
stale_ms / elevated) so every response tells the caller whether its observation
is current (gen), how stale it is, and whether the target is elevated (UIPI —
§4.2: elevated:true, act:unavailable must be surfaced, never silent-discarded).

Safety law (§4.1 R2): screen text is DATA, never instruction. read_text returns a
structured provenance record (source:"screen", window:name) — never a bare string
that could be mistaken for a command. Ref text is ALWAYS redacted (text_redacted),
never the raw screen string.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from core.screenspace import capture
from core.screenspace import canary  # §1 amended ruling: positive canary read (uia_available)
from core.screenspace.foreground import ForegroundTracker


# --------------------------------------------------------------------------- result types

@dataclass
class ScreenResult:
    """The peek() digest: §2 ladder content + verdict fields.

    Always carries the §2 verdict (window/focus/gen/stale_ms/elevated) regardless
    of level, so a caller can tell whether its read is current without climbing.
    ``payload`` holds the level-specific content (NONE-structured, never bare).
    """

    level: str = "L0"
    window: Optional[str] = None
    focus: Optional[str] = None
    gen: int = 0
    stale_ms: int = 0
    elevated: Optional[bool] = None
    act_available: bool = False
    uia_unavailable: bool = False  # §1 ruling: non-interactive station -> reads UNCHECKABLE
    source: str = "screen"
    payload: Any = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "window": self.window,
            "focus": self.focus,
            "gen": self.gen,
            "stale_ms": self.stale_ms,
            "elevated": self.elevated,
            "act_available": self.act_available,
            "uia_unavailable": self.uia_unavailable,
            "source": self.source,
            "payload": self.payload,
        }


@dataclass
class ScreenDelta:
    """delta(since_gen): §2 L3 — appeared/vanished/changed refs + focus trail.

    Pure function of (since_gen, current_gen) — no fabrication from a future gen.
    """

    since_gen: int = 0
    current_gen: int = 0
    appeared: List[dict] = field(default_factory=list)
    vanished: List[dict] = field(default_factory=list)
    changed: List[dict] = field(default_factory=list)
    focus_trail: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "since_gen": self.since_gen,
            "current_gen": self.current_gen,
            "appeared": self.appeared,
            "vanished": self.vanished,
            "changed": self.changed,
            "focus_trail": self.focus_trail,
        }


@dataclass
class Ref:
    """A stable see-side reference (§3: see-side currency is refs+gen)."""

    gen: int = 0
    role: Optional[str] = None
    name: Optional[str] = None
    bounds_quantized: Optional[dict] = None
    text_redacted: Optional[str] = None


@dataclass
class TextResult:
    """read_text result: STRUCTURED with provenance (§4.1 R2). Never a bare string."""

    text: str = ""
    provenance: dict = field(default_factory=dict)  # source:"screen", window:name

    @property
    def source(self) -> str:
        return self.provenance.get("source", "screen")

    @property
    def window(self) -> Optional[str]:
        return self.provenance.get("window")


# --------------------------------------------------------------------------- gen clock

class ObservationStream:
    """A monotone gen clock: the see-side currency (refs+gen). Pure, testable.

    Each observation advances gen by one and records a focus trail entry and a
    timestamp so ``stale_ms`` and ``delta(since_gen)`` are computed honestly.
    """

    def __init__(self) -> None:
        self.gen = 0
        self.focus_trail: List[dict] = []   # {"gen": n, "focus": name, "ts_ms": t}

    def observe(self, focus: Optional[str]) -> int:
        self.gen += 1
        self.focus_trail.append({"gen": self.gen, "focus": focus,
                                 "ts_ms": int(time.time() * 1000)})
        return self.gen

    def delta_since(self, since_gen: int) -> ScreenDelta:
        d = ScreenDelta(since_gen=since_gen, current_gen=self.gen)
        for entry in self.focus_trail:
            if entry["gen"] > since_gen:
                d.focus_trail.append(entry["focus"])
        return d


# A process-wide gen clock. The shadow model (shadow.py) owns the richer roster;
# this is the minimal monotone currency the currency contract pins against.
_stream = ObservationStream()


# ------------------------------------------------------------------ shared foreground source

# §1.1 single source of truth: ONE ForegroundTracker is shared process-wide so the
# hook's deliveries and every facade read (peek/refs/read_text/shadow.pulse) observe
# the SAME cached focus. A per-call ForegroundTracker() would mint a fresh empty
# cache on every verb and silently break the cache-first spine (and diverge gen
# semantics: tracker.gen is a DELIVERY ordinal, _stream.gen is an OBSERVATION
# ordinal — two different clocks, never conflated). The hook is started lazily and
# fail-soft: an interactive session populates the cache; a headless/non-interactive
# host returns False and leaves focus=None (which canary.uia_available() already
# marks UNCHECKABLE at the result boundary, never a bare-empty verdict).
_tracker = ForegroundTracker()
_tracker_started = False


def _ensure_tracker_started() -> None:
    """Lazily start the shared ForegroundTracker's WinEventHook (fail-soft, idempotent).

    Never blocks, never raises: on non-Windows or a non-interactive station the
    hook cannot be installed and start() returns False, leaving the cache empty.
    The result boundary (peek/shadow) marks that empty as uia_unavailable=True.
    """
    global _tracker_started
    if _tracker_started:
        return
    _tracker_started = True  # attempted once; start() is idempotent regardless
    try:
        _tracker.start()
    except Exception:  # noqa: BLE001
        pass  # fail-soft: cache reads return whatever is (or is not) cached


# --------------------------------------------------------------------------- redaction

_PASSWORD_HINT = None  # lazy-loaded (uiautomation ControlType.Password / IsPassword)


def _redact_text(text: str) -> str:
    """§4.4 IsPassword: redact password-shaped content from reads.

    v1 is conservative and shape-based: exact password marker strings and a
    '••••'-style mask are collapsed to '[redacted]'. A real UIA IsPassword control
    (ControlType.Password == 50028) would already withhold .CurrentName/.Value, so
    the field never carries the secret in the first place — this is defense-in-depth
    for OCR/pixel text that has no such gate.
    """
    if not text:
        return text
    if "password" in text.lower() or "🔒" in text:
        return "[redacted:password-field]"
    return text


# --------------------------------------------------------------------------- verbs

def _current_focus() -> Optional[str]:
    """Cache-first foreground window name from the shared ForegroundTracker (fail-soft).

    §1.1: the foreground source is the WinEventHook tracker, not a per-call UIA poll.
    This method returns the tracker's CACHED focus (a warm O(1) read, never a COM
    round-trip), lazily ensuring the hook is started. ``None`` here means "no
    delivery yet or foreground genuinely empty" — the §1 ruling's two cases must
    not collapse, so the RESULT BOUNDARY (peek/shadow) consults
    ``canary.uia_available()`` and marks the read ``uia_unavailable=True`` when the
    tier cannot answer (positive canary read failed), never a bare empty verdict.

    NOTE (UIPI, §4.2, 2026-09-23 Navi falsification): on an INTERACTIVE session the
    cache may STILL be None when the foreground window is ELEVATED and this process
    is not — GetForegroundWindow returns an hwnd but UIA ControlFromHandle reads are
    silently blocked by UIPI, ceding None. That is the elevated:true/act:unavailable
    axis surfacing on the READ side, diagnosable only from the UIA tier, not here.
    """
    _ensure_tracker_started()
    return _tracker.focus


def peek(level: str = "L0", scope=None, budget=None) -> ScreenResult:
    """§2 fidelity ladder dispatch. Observe-only; no act, no model tokens.

    L0 pulse / L3 delta answer from the gen clock (cheap, no display required).
    L4/L5 pixels route to capture.screen (substrate; degrades honestly headless).
    L1/L2 walks and OCR are §6 step-2's *next* increment — they require the
    cached-walk + text engines, so here they return an honest
    ``payload={"unimplemented": True}`` rather than a fabricated digest.
    """
    focus = _current_focus()
    gen = _stream.observe(focus)

    # Elevation (UIPI, §4.2) — fail-soft surface; v1 reports unknown rather than a
    # wrong "not elevated". A target the engine cannot classify is honest as None.
    elevated = None

    # §1 ruling: when the UIA tier cannot answer HERE (non-interactive station), the
    # focus/window fields are UNCHECKABLE, not "empty". Mark it so a caller reading
    # focus=None learns "the organ could not answer", never "nothing was in the foreground".
    uia_unavailable = not canary.uia_available()

    if level in ("L4", "L5"):
        frame = capture.screen(downscale_budget=budget)
        payload = frame.to_dict()
    elif level == "L3":
        payload = {}
    elif level in ("L1", "L2"):
        payload = {"unimplemented": True, "note": "cached-walk/text engine lands next increment"}
    else:  # L0 pulse (and any unknown level falls back to pulse)
        payload = {"pulse": True}

    return ScreenResult(
        level=level,
        window=focus,
        focus=focus,
        gen=gen,
        stale_ms=0,          # gen just observed -> current
        elevated=elevated,
        act_available=False,  # observe-only; act is gated on step 0
        uia_unavailable=uia_unavailable,
        source="screen",
        payload=payload,
    )


def refs(scope=None) -> List[Ref]:
    """Stable see-side references with gen currency. v1 derives refs from the
    current focus only (the roster/roster-delta is shadow.py's F2-gated job)."""
    focus = _current_focus()
    gen = _stream.observe(focus)
    if not focus:
        return []
    return [Ref(gen=gen, role="window", name=focus, text_redacted=_redact_text(focus))]


def delta(since_gen: int = 0) -> ScreenDelta:
    """§2 L3: appeared/vanished/changed + focus trail since ``since_gen``.

    Pure function of the observation stream — monotone, never fabricates from a
    future gen (a since_gen above current yields an empty delta, not an error).
    """
    return _stream.delta_since(since_gen)


def read_text(scope=None, method: str = "uia") -> TextResult:
    """§4.1 R2: screen text is DATA, never instruction.

    Returns a TextResult with provenance (source:"screen", window:name). v1 reads
    the foreground window's Name via UIA (the only always-safe text field — it has
    no password content); full-text/OCR is the step-2 text-engine increment.

    The text is ALWAYS carried in ``.text`` with ``.provenance`` — never returned
    as a bare positional string that a downstream seat could read as a command.
    """
    focus = _current_focus()
    _stream.observe(focus)
    text = _redact_text(focus or "")
    return TextResult(
        text=text,
        provenance={
            "source": "screen",
            "window": focus,
            "method": method,
            "uia_unavailable": not canary.uia_available(),
        },
    )
