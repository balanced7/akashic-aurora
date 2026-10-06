"""Screenspace ACTUATOR — the act half (T386 sec.6 steps 1 and 3), refusal-first.

The observe half (``peek``/``refs``/``delta``/``read_text``) shipped 2026-09-23 and cannot
change the machine. This module can, so almost all of it is about declining to.

THE SHAPE: two phases, Sunshine's mechanism adopted whole (design sec.3).
``locate()`` binds a short-lived :class:`TargetToken` token to window handle + process identity +
bounds + DPI + gen + a region screenshot hash. ``act(token, ...)`` RE-READS the world and
refuses if any bound field moved. See-side currency is refs+gen; act-side currency is tokens.

THE TARGETING LADDER, in preference order, each rung measured on this host:

1. **NAMED CONTROL.** ``ButtonControl(Name="New")`` resolves in 134-193 ms. A full depth-30
   walk of the same window is 1,027 controls / 681 named / 3,200 ms -- 17-24x slower and over
   the design's own <200 ms bar. Depth is NOT an address: ``DocumentControl(searchDepth=10)``
   returns an unnamed 0x0 node whose ValuePattern raises, while the real titled document sits
   elsewhere in the tree. Match on NAME.
2. **KEYBOARD.** The composer is a Chromium contenteditable: ZERO EditControls exist anywhere
   in the window, and its a11y nodes report 0x0 bounds. There is nothing to click, so Ctrl+N
   and the focus that follows it are the only addressable path to it.
3. **COORDINATES**, last and guarded by the region hash. This host's window origin is
   NEGATIVE -- bounds (-11,-11) 3862x2182, because the frame carries an invisible resize
   border -- at 144 dpi (150%). Pixel arithmetic is wrong twice over here by default.

TEXT GOES THROUGH THE CLIPBOARD, NOT THROUGH KEYSTROKES. ``SendKeys`` is a little language:
``{}()!+^%`` are syntax and ``{a 3}`` is a repeat count, so sending a handoff brief through it
would silently mangle every brace, paren and bang in it -- and a brief that arrives corrupted
is worse than one that never arrives, which is this house's oldest identity law. So prose is
placed on the clipboard and pasted (exact, and one hop instead of N), the operator's previous
clipboard is RESTORED afterwards, and ``SendKeys`` is reserved for short control sequences
(``{Ctrl}n``, ``{Enter}``) where the escaping surface is nil. A ``_escape_sendkeys`` helper
exists for the degraded path and is applied there, not trusted to callers.

NO SLEEPS. ``settle(predicate, timeout_s=...)`` polls a real observable and refuses with
``postcondition_failed``, reporting WHAT it waited for and HOW MANY times it looked. A sleep
long enough to pass is a step that happens to pass; it asserts nothing, so a slow frame reads
as success and the next step fires into a window that never changed.

PERMISSION IS THE HOUSE'S, NOT OURS. Every write verb resolves the seat's grant through
``core.trust.registry`` and checks a ``Cap.SCREEN_*`` tier. Those tiers are in NO role
template, so they are granted per seat with a time box and even super_admin must ask. Absence
of a cap is a refusal at the door -- the ACL's own stated law.

Pins: ``tests/test_the_actuator_refuses_before_it_acts.py``.
Design: ``docs/library/design/20260902_screenspace-organ-design_528df4.md``.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- refusal vocabulary


class RefusalCode(str, Enum):
    """Why the actuator declined. DISTINCT codes, because each carries a different remedy:
    ``not_foreground`` means focus it, ``bounds_changed`` means re-locate, ``not_capable``
    means ask the operator. Collapsing them into one failure throws the remedy away."""

    NOT_FOREGROUND       = "not_foreground"        # keystrokes would land in another window
    WINDOW_GONE          = "window_gone"           # the bound hwnd no longer resolves
    PID_CHANGED          = "pid_changed"           # hwnd reused by a different process
    BOUNDS_CHANGED       = "bounds_changed"         # moved/resized since locate()
    DPI_CHANGED          = "dpi_changed"           # monitor move or scaling change
    SCREEN_CHANGED       = "screen_changed"        # region repainted since locate()
    TOKEN_EXPIRED        = "token_expired"         # older than its TTL
    AMBIGUOUS_TARGET     = "ambiguous_target"      # >1 match; refuse, never pick
    NO_SUCH_TARGET       = "no_such_target"        # nothing matched
    NOT_CAPABLE          = "not_capable"           # seat lacks the Cap.SCREEN_* tier
    MINIMIZED            = "minimized"             # iconic: cannot be typed into
    POSTCONDITION_FAILED = "postcondition_failed"  # the effect never became observable
    NO_UIA               = "no_uia"                # substrate absent / unreadable
    BAD_VERB             = "bad_verb"              # unknown verb -- never a silent no-op
    LOCKED               = "locked"                # secure desktop / workstation locked
    DIALOG               = "dialog"                # a modal owns input


#: Which Cap each verb demands. One table, so the guard and the guarded path cannot drift --
#: the two-surfaces defect (a printer shortened while its source still emitted the long form)
#: cost an evening already.
VERB_CAPS = {
    "focus":     "screen.focus",
    "invoke":    "screen.act",
    "type":      "screen.type",
    "keys":      "screen.type",
    "click_at":  "screen.act",
    "read_back": "screen.observe",
}

#: Verbs that need the target to actually be FOREGROUND, because they dispatch input to
#: whatever is foreground rather than to the control they named.
FOREGROUND_VERBS = frozenset({"type", "keys", "click_at"})


# --------------------------------------------------------------------------- results


@dataclass(frozen=True)
class TargetToken:
    """The act-side currency: a short-lived binding to one control in one window.

    Named for the design's own vocabulary -- sec.3 writes ``locate(ref)->target_token`` and
    ``act(target_token, verb, value?)``. The shorter name ``Target`` collided with
    core/coord/target.py's class of the same name, which check_boundaries forbids because two
    same-named classes in one tree get confused in review long before they get confused by an
    import. The design's word was both free and more accurate.

    Frozen on purpose. A token a caller can edit proves nothing, because the entire mechanism
    is that :func:`act` re-reads the world and compares it to what :func:`locate` SAW.
    """

    hwnd: int
    pid: int
    exe: str
    bounds: Tuple[int, int, int, int]        # physical px, left/top/right/bottom (may be NEGATIVE)
    dpi: int                                 # GetDpiForWindow; 144 == 150% on this host
    gen: int
    frame_hash: str                          # sha256 of hash_rect's raw pixels
    name: str                                # the control name it was located BY
    role: str
    minted_at: float
    ttl_s: float
    #: The EXACT region frame_hash was taken over, as (left, top, w, h). RECORDED rather than
    #: re-derived: locate() falls back to the window rect when the control's own rect is
    #: degenerate, so a verify() that re-derived it differently would compare two different
    #: regions and refuse forever. Defaults to a zero rect meaning "no frame guard was taken" --
    #: typed absence, so the guard is SKIPPED rather than silently comparing nothing.
    hash_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def age_s(self) -> float:
        return max(0.0, time.time() - self.minted_at)

    @property
    def expired(self) -> bool:
        return self.age_s > self.ttl_s

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        """(left, top, width, height) -- the form mss wants."""
        l, t, r, b = self.bounds
        return (l, t, max(1, r - l), max(1, b - t))

    def to_dict(self) -> dict:
        return {"hwnd": self.hwnd, "pid": self.pid, "exe": self.exe, "bounds": list(self.bounds),
                "dpi": self.dpi, "gen": self.gen, "frame_hash": self.frame_hash[:16], "hash_rect": list(self.hash_rect),
                "name": self.name, "role": self.role, "age_s": round(self.age_s, 3),
                "ttl_s": self.ttl_s}


@dataclass(frozen=True)
class Located:
    """locate() result. Typed, because a bare None cannot distinguish 'absent' from
    'ambiguous' from 'no substrate' from 'not permitted' -- and those have different fixes."""

    ok: bool = False
    target: Optional[TargetToken] = None
    refusal: Optional[RefusalCode] = None
    detail: str = ""
    elapsed_ms: float = 0.0
    candidates: Tuple[str, ...] = ()          # what WAS seen, when the answer is no

    def to_dict(self) -> dict:
        return {"ok": self.ok, "refusal": self.refusal.value if self.refusal else None,
                "detail": self.detail, "elapsed_ms": round(self.elapsed_ms, 1),
                "candidates": list(self.candidates),
                "target": self.target.to_dict() if self.target else None}


@dataclass(frozen=True)
class ActResult:
    ok: bool = False
    refusal: Optional[RefusalCode] = None
    detail: str = ""
    verb: str = ""
    what: str = ""                            # the post-condition that was asserted
    observed: Optional[str] = None            # what the read-back actually saw (G3)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {"ok": self.ok, "refusal": self.refusal.value if self.refusal else None,
                "detail": self.detail, "verb": self.verb, "what": self.what,
                "observed": (self.observed[:120] if self.observed else None),
                "elapsed_ms": round(self.elapsed_ms, 1)}


@dataclass(frozen=True)
class Settled:
    """The sleep replacement's result. ``polls`` is load-bearing: 'the effect did not happen'
    and 'we never looked' are different results and only one is the window's fault."""

    ok: bool = False
    refusal: Optional[RefusalCode] = None
    what: str = ""
    polls: int = 0
    elapsed_ms: float = 0.0
    error: Optional[str] = None               # the predicate itself raised

    def to_dict(self) -> dict:
        return {"ok": self.ok, "refusal": self.refusal.value if self.refusal else None,
                "what": self.what, "polls": self.polls,
                "elapsed_ms": round(self.elapsed_ms, 1), "error": self.error}


# --------------------------------------------------------------------------- substrate (lazy)


def _uia():
    """Lazy, fail-soft, matching the package discipline: the substrate is host-installed and
    NOT a pinned repo dependency, so absence is an honest refusal and never an ImportError."""
    try:
        import uiautomation as auto  # type: ignore
        auto.SetGlobalSearchTimeout(1.0)
        return auto
    except Exception:  # noqa: BLE001
        return None


_U32 = None


def _user32():
    """A PRIVATE user32 handle with prototypes we set ourselves.

    NOT ``ctypes.windll.user32``: that object is process-global and cached, and importing
    ``uiautomation`` REWRITES its prototypes underneath us. Measured: after that import,
    ``windll.user32.GetForegroundWindow.restype`` changes c_long -> c_void_p, so the same NULL
    foreground renders as ``0`` before the import and ``None`` after it. Code comparing the
    result to an int would then silently stop matching, and the foreground guard would refuse
    forever -- a guard that always fires is a guard nobody keeps.
    """
    global _U32
    if _U32 is not None:
        return _U32
    try:
        from ctypes import wintypes
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetForegroundWindow.argtypes = []
        u.IsWindow.restype = wintypes.BOOL
        u.IsWindow.argtypes = [wintypes.HWND]
        u.IsIconic.restype = wintypes.BOOL
        u.IsIconic.argtypes = [wintypes.HWND]
        u.GetWindowTextW.restype = ctypes.c_int
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextLengthW.restype = ctypes.c_int
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.IsWindowVisible.restype = wintypes.BOOL
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.GetDpiForWindow.restype = ctypes.c_uint
        u.GetDpiForWindow.argtypes = [wintypes.HWND]
        u.OpenInputDesktop.restype = wintypes.HANDLE
        u.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        u.CloseDesktop.restype = wintypes.BOOL
        u.CloseDesktop.argtypes = [wintypes.HANDLE]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.SetForegroundWindow.restype = wintypes.BOOL
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        _U32 = u
        return u
    except Exception:  # noqa: BLE001
        return None


def workstation_locked() -> Optional[bool]:
    """True when the input desktop is unreachable -- the locked/secure desktop.

    ``OpenInputDesktop`` is the authoritative probe: on a locked workstation it fails with
    ERROR_ACCESS_DENIED (5). This is NOT the same condition as "another window has focus", and
    conflating them loses the remedy: a different foreground window can be focused, a locked
    workstation can only be waited for. Returns None when the probe itself is unavailable --
    typed absence, never a confident False.

    Measured 2026-10-06 while building this: the operator locked the screen mid-build,
    GetForegroundWindow went NULL, and windows stayed fully READABLE (IsWindow and
    GetWindowTextW both still answered for hwnd 67692). So "I can see it" proves nothing about
    "I can type into it", which is the whole reason this probe exists.
    """
    u = _user32()
    if u is None:
        return None
    try:
        ctypes.set_last_error(0)
        h = u.OpenInputDesktop(0, False, 0x0001)   # DESKTOP_READOBJECTS
        if h:
            u.CloseDesktop(h)
            return False
        # ERROR_ACCESS_DENIED (5) is the locked case. Any other failure still means we cannot
        # reach the input desktop, so the answer for an actuator is the same: do not type.
        return True
    except Exception:  # noqa: BLE001
        return None


def locked_detail() -> str:
    """The last-error context for a refusal message, so 'locked' is falsifiable by the reader."""
    try:
        return "OpenInputDesktop failed, GetLastError=%d (5 == ERROR_ACCESS_DENIED, the " \
               "locked/secure desktop)" % ctypes.get_last_error()
    except Exception:  # noqa: BLE001
        return "OpenInputDesktop failed"


def _dpi_for(hwnd: int) -> int:
    u = _user32()
    if u is None:
        return 0
    try:
        return int(u.GetDpiForWindow(hwnd))
    except Exception:  # noqa: BLE001
        return 0


def _is_iconic(hwnd: int) -> bool:
    u = _user32()
    return bool(u.IsIconic(hwnd)) if u else False


def _foreground_hwnd() -> int:
    u = _user32()
    try:
        return int(u.GetForegroundWindow()) if u else 0
    except Exception:  # noqa: BLE001
        return 0


def _pid_for(hwnd: int) -> int:
    u = _user32()
    if u is None:
        return 0
    try:
        pid = ctypes.c_ulong(0)
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:  # noqa: BLE001
        return 0


def _exe_for(pid: int) -> str:
    try:
        import psutil  # type: ignore
        return psutil.Process(pid).name()
    except Exception:  # noqa: BLE001
        return ""


def _region_sha(rect: Tuple[int, int, int, int]) -> str:
    """sha256 of ONE REGION's raw pixels.

    Deliberately not ``capture.screen()``: that returns a FULL-SCREEN frame (its ``region``
    argument is reserved and currently ignored), and a full-screen hash changes on every video
    frame anywhere on the desktop. Measured: the operator had YouTube playing while I probed,
    so a full-screen guard would have refused 100% of acts for a reason that has nothing to do
    with the target. A guard that always fires is a guard nobody keeps.
    """
    left, top, w, h = rect
    try:
        import mss  # type: ignore
        with mss.mss() as sct:
            shot = sct.grab({"left": int(left), "top": int(top),
                             "width": int(w), "height": int(h)})
            return hashlib.sha256(bytes(shot.raw)).hexdigest()
    except Exception:  # noqa: BLE001
        return ""          # empty == "not measured"; never a fake-stable constant


# --------------------------------------------------------------------------- clipboard


_CF_UNICODETEXT = 13


def _clip_get() -> Optional[str]:
    u, k = _user32(), None
    try:
        k = ctypes.windll.kernel32  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    if u is None or k is None:
        return None
    if not u.OpenClipboard(0):
        return None
    try:
        h = u.GetClipboardData(_CF_UNICODETEXT)
        if not h:
            return None
        p = k.GlobalLock(h)
        if not p:
            return None
        try:
            return ctypes.c_wchar_p(p).value
        finally:
            k.GlobalUnlock(h)
    except Exception:  # noqa: BLE001
        return None
    finally:
        u.CloseClipboard()


def _clip_set(text: str) -> bool:
    u = _user32()
    try:
        k = ctypes.windll.kernel32  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return False
    if u is None:
        return False
    data = ctypes.create_unicode_buffer(text)
    size = ctypes.sizeof(data)
    if not u.OpenClipboard(0):
        return False
    try:
        u.EmptyClipboard()
        h = k.GlobalAlloc(0x2000, size)        # GMEM_MOVEABLE
        if not h:
            return False
        p = k.GlobalLock(h)
        ctypes.memmove(p, data, size)
        k.GlobalUnlock(h)
        return bool(u.SetClipboardData(_CF_UNICODETEXT, h))
    except Exception:  # noqa: BLE001
        return False
    finally:
        u.CloseClipboard()


_SENDKEYS_SPECIAL = re.compile(r"[{}()!+^%~#]")


def _escape_sendkeys(text: str) -> str:
    """Escape text for SendKeys' little language.

    Only for the DEGRADED path -- prose goes through the clipboard. SendKeys reads ``{}()``
    as grouping, ``{a 3}`` as a repeat count, and ``!+^%`` as modifiers, so unescaped prose
    does not merely garble, it executes.
    """
    out = []
    for ch in text:
        if ch == "{":
            out.append("{{}")
        elif ch == "}":
            out.append("{}}")
        elif _SENDKEYS_SPECIAL.match(ch):
            out.append("{%s}" % ch)
        else:
            out.append(ch)
    return "".join(out)


# --------------------------------------------------------------------------- permission


def ambient_agent_id() -> str:
    """Which seat is acting. Explicit env wins; otherwise the claude seat, which holds no
    screen tier by default either -- so the fail-closed default is a REFUSAL, not an escape."""
    return (os.getenv("AKASHIC_AGENT_ID") or os.getenv("AGENT_ID") or "claude").strip()


def _capable(agent_id: Optional[str], verb: str) -> Tuple[bool, str]:
    """Resolve the seat's grant through the house ACL. Deny-by-default, checked HERE rather
    than trusted to the caller."""
    want = VERB_CAPS.get(verb)
    if want is None:
        return (False, "unknown verb %r" % (verb,))
    seat = agent_id or ambient_agent_id()
    try:
        from core.trust import registry
        from core.trust.capabilities import Cap
        grant = registry.resolve(seat)
        if grant is None:
            return (False, "no grant resolves for seat %r" % (seat,))
        if grant.has(Cap(want)):
            return (True, "%s holds %s (role=%s, expires=%s)"
                          % (seat, want, grant.role, grant.expires_at or "never"))
        # The remedy must RESTATE the seat's existing caps. `grant --caps` REPLACES the set
        # (core/trust/grant_writer.py: `eff_caps = caps_from(caps) if caps is not None else ...`),
        # so the obvious command -- naming only the new cap -- would silently strip the other
        # thirteen and cost this seat its write, exec and admin.grant authority. A remedy that
        # breaks the thing it repairs is worse than no remedy, so it is spelled out in full.
        # Also: the granter must be a SECOND PARTY. grant() raises PermissionError on
        # agent_id == by ("a second party mints your authority"), so a seat cannot hand itself
        # the desktop -- which is correct, and is why this prints a command rather than running one.
        full = sorted({c.value for c in grant.caps} | {want})
        return (False, "seat %r (role=%s) does not hold %s. A SECOND PARTY must grant it "
                       "(self-grant raises PermissionError), time-boxed, restating the existing "
                       "caps because --caps REPLACES them:\n"
                       "  py agent_cli.py grant %s --role %s --by daniil --hours 12 \\\n"
                       "    --caps %s \\\n"
                       "    --reason '<why>'"
                       % (seat, grant.role, want, seat, grant.role, ",".join(full)))
    except Exception as exc:  # noqa: BLE001 -- an unreadable ACL is a REFUSAL, never a pass
        return (False, "ACL unreadable (%s: %s) -- refusing" % (type(exc).__name__, exc))


# --------------------------------------------------------------------------- settle


def settle(predicate: Callable[[], bool], *, timeout_s: float = 3.0,
           interval_s: float = 0.05, what: str = "") -> Settled:
    """Poll a REAL observable until it holds. The only admissible wait on the act path.

    A ``time.sleep`` between steps asserts nothing: if it happens to be long enough the step
    passes, and if the frame is slow the next step fires into a window that never changed.
    This returns :class:`Settled` with ``polls`` and ``elapsed_ms`` so a failure says whether
    we looked and found nothing or never looked at all.
    """
    t0 = time.time()
    polls = 0
    err: Optional[str] = None
    deadline = t0 + max(0.0, float(timeout_s))
    while True:
        polls += 1
        try:
            if predicate():
                return Settled(ok=True, what=what, polls=polls,
                               elapsed_ms=1000 * (time.time() - t0))
        except Exception as exc:  # noqa: BLE001 -- a raising predicate is a measurement, not a crash
            err = "%s: %s" % (type(exc).__name__, exc)
        if time.time() >= deadline:
            return Settled(ok=False, refusal=RefusalCode.POSTCONDITION_FAILED, what=what,
                           polls=polls, elapsed_ms=1000 * (time.time() - t0), error=err)
        time.sleep(interval_s)      # the poll interval -- the ONE legitimate sleep here


# --------------------------------------------------------------------------- locate


def windows_matching(title: str) -> list:
    """Top-level VISIBLE windows whose title contains ``title``, as (hwnd, title) pairs.

    Win32 ``EnumWindows``, not UIA's ``GetRootControl().GetChildren()``. Measured on this host:
    the UIA walk cost **2,203 ms** -- it was the entire cost of a locate() that the targeted
    control search (195 ms) and the region hash (88 ms) finish in a fraction of. Enumerating
    top-level windows is a Win32 question and asking it through a COM accessibility tree is
    paying for a model we do not need. This brings locate() back under the design's 200 ms bar.
    """
    u = _user32()
    if u is None:
        return []
    from ctypes import wintypes
    out: list = []
    needle = title or ""
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        try:
            if not u.IsWindowVisible(hwnd):
                return True
            n = u.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            if needle in buf.value:
                out.append((int(hwnd), buf.value))
        except Exception:  # noqa: BLE001
            pass
        return True

    try:
        u.EnumWindows(CB(_cb), 0)
    except Exception:  # noqa: BLE001
        return []
    return out


def _uia_window(hwnd: int):
    """The UIA control for ONE already-chosen hwnd -- ControlFromHandle, not a tree walk."""
    auto = _uia()
    if auto is None:
        return None
    try:
        return auto.ControlFromHandle(hwnd)
    except Exception:  # noqa: BLE001
        return None


def locate(name: Optional[str] = None, role: Optional[str] = None, *,
           window_title: str = "Claude", hwnd: Optional[int] = None,
           ttl_s: float = 5.0, search_depth: int = 24,
           agent_id: Optional[str] = None) -> Located:
    """Phase one: bind a token to a named control in one unambiguous window.

    Args:
        name: the control's UIA Name. This is the ADDRESS -- see the ladder in the module
            docstring. ``None`` binds the window itself (for keyboard-only verbs).
        role: UIA control type without the ``Control`` suffix ("Button", "Document", ...).
        window_title: substring match on the top-level window name.
        hwnd: disambiguate explicitly when more than one window matches. This is the remedy
            for ``AMBIGUOUS_TARGET``; a refusal with no path forward is a dead end, not a guard.
    """
    t0 = time.time()

    def done(**kw) -> Located:
        return Located(elapsed_ms=1000 * (time.time() - t0), **kw)

    auto = _uia()
    if auto is None:
        return done(refusal=RefusalCode.NO_UIA,
                    detail="uiautomation substrate not importable on this host")

    wins = windows_matching(window_title)
    if hwnd is not None:
        wins = [w for w in wins if w[0] == int(hwnd)]
    if not wins:
        return done(refusal=RefusalCode.NO_SUCH_TARGET,
                    detail="no visible top-level window matching %r%s"
                           % (window_title, " with hwnd %s" % hwnd if hwnd else ""))
    if len(wins) > 1:
        return done(
            refusal=RefusalCode.AMBIGUOUS_TARGET,
            candidates=tuple("%s(hwnd=%s,pid=%s)" % (t, h, _pid_for(h)) for h, t in wins[:8]),
            detail="%d windows match %r -- refusing to pick. Pass hwnd=<n>. Picking the first "
                   "would be a coin flip over which live session receives the input."
                   % (len(wins), window_title))

    whandle, wtitle = wins[0]
    if _is_iconic(whandle):
        return done(refusal=RefusalCode.MINIMIZED,
                    detail="window %s (%r) is minimized; restore it before locating a control"
                           % (whandle, wtitle))

    win = _uia_window(whandle)
    if win is None:
        return done(refusal=RefusalCode.NO_UIA,
                    detail="ControlFromHandle(%s) returned nothing -- the window exists to "
                           "Win32 but not to UIA" % whandle)
    ctrl = win
    if name:
        try:
            getter = getattr(win, "%sControl" % (role or "")) if role else None
            ctrl = (getter(searchDepth=search_depth, Name=name) if getter
                    else win.Control(searchDepth=search_depth, Name=name))
            if not ctrl.Exists(0.5, 0.1):
                return done(refusal=RefusalCode.NO_SUCH_TARGET,
                            detail="no %s named %r within depth %d of %r"
                                   % (role or "control", name, search_depth, wtitle))
        except Exception as exc:  # noqa: BLE001
            return done(refusal=RefusalCode.NO_SUCH_TARGET,
                        detail="targeted search for %r failed: %s: %s"
                               % (name, type(exc).__name__, exc))

    try:
        r = ctrl.BoundingRectangle
        bounds = (int(r.left), int(r.top), int(r.right), int(r.bottom))
        wr = win.BoundingRectangle
        wbounds = (int(wr.left), int(wr.top), int(wr.right), int(wr.bottom))
    except Exception as exc:  # noqa: BLE001
        return done(refusal=RefusalCode.WINDOW_GONE, detail="bounds unreadable: %s" % exc)

    pid = _pid_for(whandle) or int(getattr(win, "ProcessId", 0) or 0)
    bound_rect = bounds if name else wbounds

    # Hash the CONTROL's own region when it has one, and fall back to the window only when the
    # control reports a degenerate rect -- which Chromium a11y nodes do (measured: every
    # DocumentControl in this window reports 0x0, so a control-rect hash there would be the
    # hash of nothing and would compare equal forever).
    #
    # Scope matters in BOTH directions. A window-wide hash costs 88 ms over 8.4M pixels AND
    # changes whenever anything in the window repaints -- a streaming reply alone would trip it
    # on every act. The Button's own 404x39 strip hashes in ~1 ms and changes only when the
    # thing we are about to click changes, which is the question the guard is actually asking.
    hl, ht, hr, hb = bound_rect
    degenerate = (hr - hl) <= 1 or (hb - ht) <= 1
    hash_rect = ((wbounds[0], wbounds[1],
                  max(1, wbounds[2] - wbounds[0]), max(1, wbounds[3] - wbounds[1]))
                 if degenerate else (hl, ht, max(1, hr - hl), max(1, hb - ht)))

    tgt = TargetToken(hwnd=whandle, pid=pid, exe=_exe_for(pid),
                 bounds=bound_rect,
                 dpi=_dpi_for(whandle), gen=_gen_now(),
                 frame_hash=_region_sha(hash_rect), hash_rect=hash_rect,
                 name=name or wtitle, role=role or "Window",
                 minted_at=time.time(), ttl_s=float(ttl_s))
    return done(ok=True, target=tgt, detail="bound %s %r in %r (pid %s, dpi %s)"
                                            % (tgt.role, tgt.name, wtitle, tgt.pid, tgt.dpi))


def _gen_now() -> int:
    """Borrow the observe half's gen clock when it is running; otherwise a monotone tick.

    The design's rule is that see-side currency is refs+gen, so the act side must stamp the
    SAME clock where one exists rather than minting a private counter nobody can correlate.
    """
    try:
        from core.screenspace import engine
        stream = getattr(engine, "_STREAM", None)
        g = getattr(stream, "gen", None)
        if isinstance(g, int):
            return g
    except Exception:  # noqa: BLE001
        pass
    return int(time.time() * 1000) & 0x7FFFFFFF


# --------------------------------------------------------------------------- verify the token


def verify(target: TargetToken, *, require_foreground: bool = False,
           require_frame: bool = False) -> Optional[ActResult]:
    """Re-read the world and compare it to what ``locate`` saw. Returns a refusal, or None
    when the token still describes reality."""
    t0 = time.time()

    def no(code: RefusalCode, detail: str) -> ActResult:
        return ActResult(ok=False, refusal=code, detail=detail, verb="verify",
                         elapsed_ms=1000 * (time.time() - t0))

    if target.expired:
        return no(RefusalCode.TOKEN_EXPIRED,
                  "token is %.1fs old, ttl %.1fs -- re-locate" % (target.age_s, target.ttl_s))

    u = _user32()
    if u is None:
        return no(RefusalCode.NO_UIA, "user32 unavailable")
    try:
        if not u.IsWindow(target.hwnd):
            return no(RefusalCode.WINDOW_GONE, "hwnd %s is no longer a window" % target.hwnd)
    except Exception as exc:  # noqa: BLE001
        return no(RefusalCode.WINDOW_GONE, "IsWindow failed: %s" % exc)

    pid_now = _pid_for(target.hwnd)
    if pid_now and target.pid and pid_now != target.pid:
        return no(RefusalCode.PID_CHANGED,
                  "hwnd %s now belongs to pid %s, not %s (handles are reused)"
                  % (target.hwnd, pid_now, target.pid))

    if _is_iconic(target.hwnd):
        return no(RefusalCode.MINIMIZED, "window %s was minimized since locate" % target.hwnd)

    dpi_now = _dpi_for(target.hwnd)
    if target.dpi and dpi_now and dpi_now != target.dpi:
        return no(RefusalCode.DPI_CHANGED,
                  "dpi moved %s -> %s (monitor move or scaling change); every coordinate the "
                  "token carries is now wrong" % (target.dpi, dpi_now))

    if require_foreground:
        # LOCKED is checked FIRST and reported separately: a locked workstation and a
        # different-window-has-focus are both "not foreground" but have opposite remedies --
        # one can be focused, the other can only be waited for. Measured on this host: with the
        # screen locked, windows stayed fully READABLE (IsWindow and GetWindowTextW both
        # answered for hwnd 67692) while the input desktop was unreachable. Being able to SEE a
        # window proves nothing about being able to type into it.
        if workstation_locked():
            return no(RefusalCode.LOCKED,
                      "the workstation is locked -- %s. The window is still readable, which is "
                      "exactly why this is checked rather than inferred from a successful "
                      "locate()." % locked_detail())
        fg = _foreground_hwnd()
        if fg != target.hwnd:
            return no(RefusalCode.NOT_FOREGROUND,
                      "foreground is hwnd %s, target is %s. Keystrokes follow the FOREGROUND "
                      "window, not the control that was located -- typing now would land in "
                      "whatever the operator is looking at." % (fg, target.hwnd))

    if require_frame and target.frame_hash:
        now = _region_sha(target.hash_rect)
        if now and now != target.frame_hash:
            return no(RefusalCode.SCREEN_CHANGED,
                      "the target region repainted since locate (%s -> %s); a coordinate click "
                      "would land on whatever moved there"
                      % (target.frame_hash[:12], now[:12]))
    return None


# --------------------------------------------------------------------------- act


def act(target: TargetToken, verb: str, value: Optional[str] = None, *,
        expect: Optional[Callable[[], bool]] = None, expect_what: str = "",
        timeout_s: float = 3.0, require_foreground: Optional[bool] = None,
        restore_clipboard: bool = True, agent_id: Optional[str] = None) -> ActResult:
    """Phase two: do one thing, having first refused every reason not to.

    Order is deliberate: CAPABILITY, then TOKEN VALIDITY, then the action, then the asserted
    POST-CONDITION. Checking capability last would mean a refused seat had already moved the
    operator's focus.

    Args:
        verb: ``focus`` | ``invoke`` | ``type`` | ``keys`` | ``click_at`` | ``read_back``.
        expect: the post-condition. When given, the verb only reports ok if this becomes true
            within ``timeout_s``. Without it a ``type`` can report that keys were DISPATCHED,
            never that they ARRIVED (G3).
    """
    t0 = time.time()

    def no(code: RefusalCode, detail: str, observed: Optional[str] = None) -> ActResult:
        return ActResult(ok=False, refusal=code, detail=detail, verb=verb, what=expect_what,
                         observed=observed, elapsed_ms=1000 * (time.time() - t0))

    if verb not in VERB_CAPS:
        return no(RefusalCode.BAD_VERB,
                  "unknown verb %r; known: %s" % (verb, ", ".join(sorted(VERB_CAPS))))

    allowed, why = _capable(agent_id, verb)
    if not allowed:
        return no(RefusalCode.NOT_CAPABLE, why)

    need_fg = (verb in FOREGROUND_VERBS) if require_foreground is None else require_foreground
    bad = verify(target, require_foreground=need_fg, require_frame=(verb == "click_at"))
    if bad is not None:
        return ActResult(ok=False, refusal=bad.refusal, detail=bad.detail, verb=verb,
                         what=expect_what, elapsed_ms=1000 * (time.time() - t0))

    auto = _uia()
    if auto is None:
        return no(RefusalCode.NO_UIA, "uiautomation substrate absent")

    observed: Optional[str] = None
    clip_restore: Optional[str] = None       # set by `type`; replayed only AFTER expect settles,
    #                                          because a paste is asynchronous in the target app
    #                                          and restoring early makes Ctrl+V paste the OLD
    #                                          clipboard -- a silent, exact-looking corruption.
    try:
        if verb == "focus":
            u = _user32()
            u.SetForegroundWindow(target.hwnd)
            got = settle(lambda: _foreground_hwnd() == target.hwnd,
                         timeout_s=timeout_s, what="window %s is foreground" % target.hwnd)
            if not got.ok:
                return no(RefusalCode.NOT_FOREGROUND,
                          "SetForegroundWindow did not take after %d polls / %.0f ms -- Windows "
                          "refuses foreground changes from a process without recent input"
                          % (got.polls, got.elapsed_ms))

        elif verb == "invoke":
            ctrl = _rebind(target)
            if ctrl is None:
                return no(RefusalCode.NO_SUCH_TARGET,
                          "control %r no longer resolves for invoke" % target.name)
            # InvokePattern over a synthetic click: it reaches the control directly, so it does
            # not depend on the control being visible, unobscured, or at the cached coordinate.
            if _has_invoke(ctrl):
                ctrl.GetInvokePattern().Invoke()
            else:
                ctrl.Click(waitTime=0)

        elif verb == "keys":
            if not value:
                return no(RefusalCode.BAD_VERB, "keys needs a value, e.g. '{Ctrl}n'")
            auto.SendKeys(value, waitTime=0)

        elif verb == "type":
            if value is None:
                return no(RefusalCode.BAD_VERB, "type needs a value")
            prev = _clip_get() if restore_clipboard else None
            if _clip_set(value):
                auto.SendKeys("{Ctrl}v", waitTime=0)
                clip_restore = prev          # replayed at the very end, after expect settles
            else:
                # Degraded path: escape, because unescaped prose does not garble, it EXECUTES
                # -- SendKeys reads {}() as grouping and !+^% as modifiers.
                auto.SendKeys(_escape_sendkeys(value), waitTime=0)

        elif verb == "click_at":
            l, t, r, b = target.bounds
            auto.Click(int((l + r) // 2), int((t + b) // 2), waitTime=0)

        elif verb == "read_back":
            ctrl = _rebind(target)
            observed = _read_value(ctrl) if ctrl is not None else None

    except Exception as exc:  # noqa: BLE001
        return no(RefusalCode.POSTCONDITION_FAILED,
                  "%s raised during %r: %s" % (type(exc).__name__, verb, exc))

    try:
        if expect is not None:
            got = settle(expect, timeout_s=timeout_s,
                         what=expect_what or "the post-condition for %r" % verb)
            if not got.ok:
                return ActResult(ok=False, refusal=RefusalCode.POSTCONDITION_FAILED,
                                 detail="%r dispatched but its effect never became observable "
                                        "(%d polls / %.0f ms)%s"
                                        % (verb, got.polls, got.elapsed_ms,
                                           "; predicate raised %s" % got.error if got.error
                                           else ""),
                                 verb=verb, what=got.what, observed=observed,
                                 elapsed_ms=1000 * (time.time() - t0))
    finally:
        if clip_restore is not None:
            _clip_set(clip_restore)          # the operator's clipboard is theirs, not ours

    return ActResult(ok=True, verb=verb, what=expect_what, observed=observed,
                     detail="%s ok" % verb, elapsed_ms=1000 * (time.time() - t0))


def _rebind(target: TargetToken):
    """Re-resolve the control the token names. Tokens bind IDENTITY, not live COM pointers:
    a stored pointer can go stale silently, while a name re-resolves or honestly fails."""
    win = _uia_window(target.hwnd)
    if win is None:
        return None
    if not target.name or target.role == "Window":
        return win
    try:
        getter = getattr(win, "%sControl" % target.role, None)
        ctrl = (getter(searchDepth=24, Name=target.name) if getter
                else win.Control(searchDepth=24, Name=target.name))
        return ctrl if ctrl.Exists(0.4, 0.1) else None
    except Exception:  # noqa: BLE001
        return None


def _has_invoke(ctrl) -> bool:
    try:
        return ctrl.GetInvokePattern() is not None
    except Exception:  # noqa: BLE001
        return False


def _read_value(ctrl) -> Optional[str]:
    """G3's read-back. Tries Value then Text; returns None when neither is exposed, because
    'the control has no readable value' and 'the value is empty' are different facts."""
    for getter in ("GetValuePattern", "GetTextPattern"):
        try:
            pat = getattr(ctrl, getter)()
            if pat is None:
                continue
            if getter == "GetValuePattern":
                return pat.Value
            return pat.DocumentRange.GetText(8000)
        except Exception:  # noqa: BLE001
            continue
    return None
