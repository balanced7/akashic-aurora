"""RED pins: the screenspace organ can SEE but cannot ACT, and the act half must refuse first.

PRE-REGISTRATION (M3). RED at this commit; the module follows separately.

DANIEL, 2026-10-06, after I hand-drove his desktop to create a session: "How do we iterate on
this to make it more reliable and easier?" then "Lets build those and verbify the Ctrl + N and
handoff + start new session combo." This file is build steps 1 and 3 of the ratified design
(docs/library/design/20260902_screenspace-organ-design_528df4.md sec.6): "RED contracts: refusal
matrix (wrong window/stale/focus-theft/DPI/dialog/locked/unapproved) + G4 injection pin + G3
act-verify pin." The compound verb is step 5, already named `desktop_prompt` there.

WHY EVERY PIN BELOW IS A MEASUREMENT AND NOT A WORRY. All numbers taken on this host tonight
against the live Claude window, hwnd 67692 / pid 24836 / claude.exe (the MSIX build):

  (a) FOCUS THEFT IS THE LIVE CASE, NOT THE EDGE CASE. At the moment I probed, the Claude
      window was fully locatable -- and `user32.GetForegroundWindow()` returned **133616**,
      a different window ('YouTube - Brave'). Keyboard input goes to the FOREGROUND window,
      never to the control you "located". So a locate() that succeeds tells you nothing about
      where your keystrokes will land. Had I run the Ctrl+N sequence on the strength of a
      successful locate, I would have typed a handoff brief into Daniel's YouTube tab. This is
      the pin I care about most and it was true on the first probe, unprompted.

  (b) NAME-FIRST BEATS A WALK BY 17-24x, AND DEPTH ALONE FINDS THE WRONG CONTROL.
      Full depth-30 walk of the window: 1,027 controls, 681 named, **3,200 ms** -- which blows
      the design's own <200ms tree/find bar (sec.5). Targeted `ButtonControl(Name="New")`:
      **134-193 ms**, correct rect (12,66)+404x39, at searchDepth 18/20/24 alike.
      But matching on TYPE+DEPTH instead of NAME silently finds a different element:
      `win.DocumentControl(searchDepth=10)` returns an UNNAMED 0x0 control whose
      ValuePattern raises AttributeError, while the real titled document lives elsewhere in
      the tree. Depth is not an address. NAME is the address.

  (c) THERE IS NO COMPOSER CONTROL TO CLICK. Zero EditControls exist anywhere in the window
      (426 ms exhaustive scan). The composer is a Chromium contenteditable whose a11y nodes
      report 0x0 bounds. Daniel's instinct -- "click at x coordinates then tab till text box"
      -- cannot bind to a control, which is exactly why the ladder must put KEYBOARD above
      COORDINATES and why typing can only be verified by reading the text back (pin G3).

  (d) DPI IS A REAL DIVERGENCE, NOT A ROUNDING ERROR. `GetDpiForWindow(67692)` = **144**
      (150% scaling). UIA/mss report physical pixels; PyGetWindow reports logical. The window
      bounds come back **(-11,-11) 3862x2182** -- origin NEGATIVE, because the frame includes
      an invisible resize border. Any coordinate arithmetic that assumes a 0,0 origin and a
      96-dpi scale is wrong twice over on this host.

  (e) EXACTLY ONE WINDOW MATCHED 'Claude' AT PROBE TIME. One is today's luck, not a contract:
      a second desktop window (or a Brave tab titled 'Claude') makes "the first match" a
      coin flip on which live session gets the keystrokes. Ambiguity must refuse, never pick.

THE HOUSE ALREADY HAS THE PERMISSION MECHANISM, so this does not build a second one.
`core/trust/capabilities.py` carries the Cap vocabulary and ROLE_TEMPLATES; `core/trust/
registry.py` resolves an agent's effective caps with time boxes. The design's tiers
(`screen.observe / focus / type / act / launch / privileged`, sec.3) belong in THAT enum.
Deny-by-default is already the stated law there -- "absence of a cap = the action is refused at
the door" -- so adding the screen caps to the vocabulary WITHOUT adding them to any role
template is the fail-closed default the design asks for ("read-only stays default, only
authenticated daniil may request privileged profile"). Even super_admin must be granted them
explicitly, time-boxed.

Run::

    py -m pytest tests/test_the_actuator_refuses_before_it_acts.py -q
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:                                      # deliberately NOT importorskip: the module's absence
    from core.screenspace import act      # is the FIRST RED pin, and a skipped pin is a pin
    _IMPORT_ERROR = None                  # that reports green forever.
except Exception as exc:                  # noqa: BLE001
    act = None                            # type: ignore[assignment]
    _IMPORT_ERROR = exc


@pytest.fixture(autouse=True)
def _require_the_module():
    """FAIL, never skip, while the actuator is unbuilt. A pre-registered pin that skips when its
    subject is missing is indistinguishable from a passing one in CI output -- which is how a
    built-ahead module stays unwired for two months (`capability_without_a_door`)."""
    if act is None:
        pytest.fail("core/screenspace/act.py does not import: %r" % (_IMPORT_ERROR,))


# ------------------------------------------------------------------ the module and its door
def test_the_act_module_exists():
    """THE FIRST PIN, asserted without importorskip so a missing module FAILS rather than skips.

    The observe half shipped on 2026-09-23 and `core/screenspace/__init__.py` says the act
    verbs are "deliberately NOT exported here", gated on the operator unlock. That gate is now
    open by Daniel's explicit order, and a capability whose gate opens but whose door does not
    is this house's recurring defect (`capability_without_a_door`). The gate belongs IN the
    code, enforced per call against the ACL -- not in the module's absence from the package.
    """
    import importlib
    m = importlib.import_module("core.screenspace.act")
    for fn in ("locate", "act", "settle"):
        assert hasattr(m, fn), f"core.screenspace.act has no {fn}()"


def test_the_package_door_exposes_act():
    """A capability reachable only by a deep import is one the fleet will not find."""
    import core.screenspace as ss
    assert "act" in getattr(ss, "__all__", ()), (
        "core.screenspace.__all__ does not list 'act'. The observe verbs are on the flat seam; "
        "an actuator reachable only via `from core.screenspace.act import ...` is the "
        "capability_without_a_door shape that kept precision_audit.py dead for two months.")


# ------------------------------------------------------------------ the two-phase token
def test_locate_binds_all_six_identity_fields():
    """Sunshine's two-phase mechanism, adopted whole (design sec.3): locate() binds a short-lived
    token to window handle + process identity + bounds + DPI + gen + screenshot hash.

    A token missing any one of those cannot detect the corresponding change, and `act(token)`
    is only as safe as the weakest field it bound.
    """
    got = act.locate(name="New", role="Button")
    assert hasattr(got, "ok") and hasattr(got, "refusal"), (
        "locate() must return a typed result carrying .ok and .refusal, never a bare control "
        "or None -- 'zero is not no' applies to targeting too: a None could mean 'absent', "
        "'ambiguous', 'no UIA' or 'not permitted', and those have different fixes.")
    if not got.ok:
        pytest.skip(f"no live window to bind on this host: {got.refusal} / {got.detail}")
    t = got.target
    for field in ("hwnd", "pid", "exe", "bounds", "dpi", "gen", "frame_hash"):
        assert getattr(t, field, None) is not None, (
            f"the target token does not bind {field!r}; act() cannot refuse on a change it "
            f"never recorded")
    assert t.dpi > 0, "dpi bound as %r -- GetDpiForWindow returned 144 on this host" % (t.dpi,)
    assert t.ttl_s and t.ttl_s > 0, "a token with no TTL is not short-lived"


def test_the_token_is_immutable():
    """A token a caller can edit is a token that proves nothing: the whole mechanism is that
    act() re-reads the world and compares it to what locate() SAW."""
    got = act.locate(name="New", role="Button")
    if not got.ok:
        pytest.skip(f"no live window: {got.refusal}")
    with pytest.raises(Exception):
        got.target.hwnd = 1  # type: ignore[misc]


# ------------------------------------------------------------------ the refusal matrix
def test_refusal_codes_cover_the_whole_matrix():
    """Design sec.6 step 1 names the matrix: wrong window / stale / focus-theft / DPI / dialog /
    locked / unapproved. Each must be a DISTINCT code, because each has a different remedy --
    'not foreground' means focus it, 'bounds changed' means re-locate, 'not capable' means ask
    the operator. Collapsing them into one failure throws away the remedy.
    """
    codes = {c.value for c in act.RefusalCode}
    for required in ("not_foreground", "window_gone", "pid_changed", "bounds_changed",
                     "dpi_changed", "screen_changed", "token_expired", "ambiguous_target",
                     "no_such_target", "not_capable", "minimized", "postcondition_failed",
                     "no_uia"):
        assert required in codes, f"RefusalCode has no {required!r}; the matrix is incomplete"


def test_act_refuses_when_the_target_is_not_the_foreground_window():
    """**THE PIN THIS FILE EXISTS FOR**, and the one that was live on the first probe.

    Measured: the Claude window (hwnd 67692) was locatable while GetForegroundWindow() returned
    133616 -- a Brave window playing YouTube. Keystrokes follow the FOREGROUND window, not the
    located control. An actuator that types on the strength of a successful locate() types into
    whatever the operator happens to be looking at.

    A typing verb must therefore either refuse with not_foreground, or focus the target FIRST
    and verify it took. It must never type blind.
    """
    fake = act.TargetToken(hwnd=67692, pid=24836, exe="claude.exe", bounds=(-11, -11, 3851, 2171),
                      dpi=144, gen=1, frame_hash="deadbeef", name="New", role="Button",
                      minted_at=0.0, ttl_s=5.0)
    r = act.act(fake, "type", "hello", require_foreground=True)
    assert not r.ok, "act() typed into a target it never confirmed was foreground"
    assert r.refusal in (act.RefusalCode.NOT_FOREGROUND, act.RefusalCode.TOKEN_EXPIRED,
                         act.RefusalCode.NOT_CAPABLE, act.RefusalCode.BOUNDS_CHANGED), (
        "refused with %r; expected a foreground/staleness/capability refusal" % (r.refusal,))


def test_act_refuses_a_token_whose_window_is_gone():
    """Handle reuse is real: Windows recycles HWNDs. A token bound to a dead handle must refuse
    on window_gone or pid_changed, never act on whatever now answers to that number."""
    dead = act.TargetToken(hwnd=0x7FFFFFFE, pid=999999, exe="claude.exe", bounds=(0, 0, 10, 10),
                      dpi=96, gen=1, frame_hash="x", name="New", role="Button",
                      minted_at=0.0, ttl_s=60.0)
    r = act.act(dead, "focus")
    assert not r.ok
    assert r.refusal in (act.RefusalCode.WINDOW_GONE, act.RefusalCode.PID_CHANGED,
                         act.RefusalCode.NOT_CAPABLE, act.RefusalCode.TOKEN_EXPIRED)


def test_act_refuses_an_expired_token():
    """`minted_at=0.0` is 1970. A token with a TTL that does not expire is not short-lived, and
    'short-lived' is the entire reason the token is safer than a coordinate."""
    stale = act.TargetToken(hwnd=67692, pid=24836, exe="claude.exe", bounds=(-11, -11, 3851, 2171),
                       dpi=144, gen=1, frame_hash="x", name="New", role="Button",
                       minted_at=0.0, ttl_s=5.0)
    r = act.act(stale, "focus")
    assert not r.ok
    assert r.refusal in (act.RefusalCode.TOKEN_EXPIRED, act.RefusalCode.NOT_CAPABLE)


def test_more_than_one_matching_window_is_ambiguous_rather_than_the_first_one():
    """Exactly one window matched 'Claude' tonight. That is luck, not a contract: a second
    desktop window -- or a browser tab titled 'Claude' -- makes "the first match" a coin flip
    over which LIVE SESSION receives the keystrokes. The kill-drill list (design sec.6 step 8)
    names 'duplicate-agent race' for exactly this.
    """
    src = inspect.getsource(act)
    assert "AMBIGUOUS_TARGET" in src or "ambiguous_target" in src, (
        "nothing in act.py ever raises ambiguity; a multi-match must refuse, not pick")
    sig = inspect.signature(act.locate)
    assert "hwnd" in sig.parameters or "window_hwnd" in sig.parameters, (
        "locate() offers no way to disambiguate by handle, so a caller facing AMBIGUOUS_TARGET "
        "has no remedy -- a refusal with no path forward is a dead end, not a guard")


# ------------------------------------------------------------------ the capability gate
def test_the_screen_caps_exist_in_the_houses_own_vocabulary():
    """Not a second permission system. core/trust/capabilities.py already states the law --
    "absence of a cap = the action is refused at the door" -- and already carries time boxes
    and an audit trail through core/trust/registry.py.
    """
    from core.trust.capabilities import Cap
    vals = {c.value for c in Cap}
    for tier in ("screen.observe", "screen.focus", "screen.type", "screen.act",
                 "screen.launch", "screen.privileged"):
        assert tier in vals, (
            f"Cap has no {tier!r}. The design names these six tiers (sec.3) so a seat can hold "
            f"observe+type without launch or destructive click; inventing a parallel gate inside "
            f"act.py would leave them outside the ACL's time boxes and audit trail.")


def test_no_role_template_grants_the_act_tiers_by_default():
    """FAIL-CLOSED, and it is the design's own words: "read-only stays default, only
    authenticated daniil may request privileged profile". An actuator that any admin seat holds
    implicitly is one that fires the first time a seat mistakes a desktop for a sandbox.
    Even super_admin must be granted these explicitly and time-boxed.
    """
    from core.trust.capabilities import Cap, ROLE_TEMPLATES
    dangerous = {Cap("screen.type"), Cap("screen.act"), Cap("screen.launch"),
                 Cap("screen.privileged")}
    for role, tpl in ROLE_TEMPLATES.items():
        held = set(tpl.get("caps") or ()) & dangerous
        assert not held, (
            f"role {role!r} holds {sorted(c.value for c in held)} by default -- the act tiers "
            f"must be granted per seat with a time box, never inherited from a role")


def test_act_refuses_when_the_seat_lacks_the_cap():
    """Deny-by-default, checked at the act() door rather than trusted to the caller."""
    t = act.TargetToken(hwnd=67692, pid=24836, exe="claude.exe", bounds=(-11, -11, 3851, 2171),
                   dpi=144, gen=1, frame_hash="x", name="New", role="Button",
                   minted_at=0.0, ttl_s=5.0)
    r = act.act(t, "type", "hello", agent_id="quarantined-nobody")
    assert not r.ok, "a seat with no screen.type cap typed anyway"


# ------------------------------------------------------------------ post-conditions, not sleeps
def test_the_act_path_never_sleeps_as_a_postcondition():
    """THE RELIABILITY PIN. Last night I drove this desktop with `time.sleep()` between steps
    and it worked -- which is the problem: a sleep that happens to be long enough is a test
    that happens to pass. A sleep asserts nothing, so a slow frame reads as success and the
    next step fires into a window that never changed.

    `settle(predicate, timeout_s=...)` is the replacement: poll a REAL observable until it is
    true, and refuse with postcondition_failed when it never becomes true. A bare sleep on the
    act path is therefore a defect, not a style choice.
    """
    src = inspect.getsource(act)
    body = re.sub(r'"""(?:.|\n)*?"""', "", src)          # docstrings may DISCUSS sleeping
    body = re.sub(r"#.*", "", body)                       # so may comments
    offenders = [ln.strip() for ln in body.splitlines()
                 if re.search(r"\btime\.sleep\s*\(", ln)
                 and "interval" not in ln and "_poll" not in ln]
    assert not offenders, (
        "act.py sleeps as a wait-for-effect: %r. The only admissible sleep is the poll "
        "interval inside settle()." % (offenders[:4],))


def test_settle_refuses_rather_than_returning_false_when_the_predicate_never_holds():
    """Typed absence again: a bare False cannot distinguish 'the effect did not happen' from
    'the predicate itself blew up' from 'we never looked'."""
    out = act.settle(lambda: False, timeout_s=0.05, what="a thing that never happens")
    assert hasattr(out, "ok") and out.ok is False
    assert getattr(out, "refusal", None) == act.RefusalCode.POSTCONDITION_FAILED
    assert getattr(out, "what", None), "settle() does not report WHAT it was waiting for"
    assert getattr(out, "polls", 0) >= 1, (
        "settle() reported a failure without ever polling -- 'did not happen' and 'never "
        "looked' are different results and only one of them is the window's fault")


def test_settle_returns_promptly_once_the_predicate_holds():
    """A post-condition must be FASTER than the sleep it replaces, or it will not be adopted.
    The design's bar is observe->locate->act < 350 ms."""
    calls = {"n": 0}

    def pred():
        calls["n"] += 1
        return calls["n"] >= 2

    out = act.settle(pred, timeout_s=5.0, what="second poll")
    assert out.ok, "settle() did not detect a predicate that became true"
    assert out.elapsed_ms < 1000, (
        "settle() took %.0f ms to notice a predicate true on its second poll" % out.elapsed_ms)


# ------------------------------------------------------------------ G3: act-verify
def test_typing_is_verified_by_reading_it_back():
    """G3 ACT-VERIFY, and (c) above is why it is mandatory rather than nice: the composer is a
    Chromium contenteditable with no EditControl and 0x0 bounds, so the ONLY evidence that text
    landed is reading it back. A type verb that reports success from the fact that it dispatched
    keystrokes is reporting that it tried.
    """
    sig = inspect.signature(act.act)
    assert "expect" in sig.parameters or "verify" in sig.parameters, (
        "act() has no way to state the expected post-state, so a 'type' can only ever report "
        "that keys were dispatched -- never that they arrived")


# ------------------------------------------------------------------ the ladder
def test_coordinates_are_the_last_rung_and_are_hash_guarded():
    """Preference order, established with Daniel tonight: named control -> keyboard shortcut ->
    coordinates. Coordinates are last because of (b) and (d): a 17-24x slower walk is still a
    better address than a pixel, and this host's window origin is NEGATIVE at 144 dpi. When
    coordinates are unavoidable they must be guarded by the screenshot hash the token bound, so
    a repaint between locate and act refuses instead of clicking a moved button.
    """
    src = inspect.getsource(act)
    assert "frame_hash" in src, "act.py never consults the bound screenshot hash"
    low = src.lower()
    assert "coordinate" in low or "click_at" in low or "coord" in low, (
        "act.py has no coordinate rung at all; the escape hatch must EXIST and be guarded, "
        "not be absent -- the composer has no clickable control, so some path must remain")
