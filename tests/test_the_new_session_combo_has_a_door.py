"""Pins: the Ctrl+N + handoff + start-new-session combo, and its door.

Daniel, 2026-10-06: "Lets build those and verbify the Ctrl + N and handoff + start new session
combo." Design sec.6 step 5 already named it ``desktop_prompt``.

WHY THE COMBO NEEDS ITS OWN PINS AND NOT JUST THE ACTUATOR'S. The actuator's pins
(``test_the_actuator_refuses_before_it_acts.py``) cover ONE action at a time. A combo fails
differently: it fails by CARRYING ON. Last night the same sequence worked by hand with
``time.sleep()`` between steps, which is not a verb but an anecdote -- nothing asserted anything,
so the only reason it worked is that the frames happened to arrive in time. The specific danger
is a chain that proceeds past a failed focus, because the next step then types a handoff brief
into whatever window the operator actually has in front of them.

THE RECEIPT IS A FILE, NOT A PIXEL. Claude Desktop writes one JSONL per session under
``~/.claude/projects/<slug>/`` -- measured: 56 transcripts in ``C:\\Users\\L5\\.claude\\
projects\\E--`` on this host. So "did a new session start and did it receive MY text" is
answerable on the filesystem rather than by screenshot, which is the causal proof design sec.6
step 4 asks for and the one thing the UI cannot fake.

MEASURED STATE OF THE DOOR WHEN THESE WERE WRITTEN, which is also why no live drill runs here:
``py agent_cli.py screen status`` reported ``locked=True foreground_hwnd=0``, the window found
at hwnd 67692 / pid 24836 / dpi 144, and **verbs permitted: NONE** -- because the ``screen.*``
tiers sit in no role template, so even the super_admin claude seat holds none of them. Both of
those are correct refusals, and together they mean the combo cannot be drilled unattended. That
is the design's intent (step 4 is "attended"), not a gap in these pins.

Run::

    py -m pytest tests/test_the_new_session_combo_has_a_door.py -q
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.screenspace import combo as C  # noqa: E402

CLI = str(ROOT / "agent_cli.py")


def _run(*args, timeout=120):
    return subprocess.run([sys.executable, "-X", "utf8", CLI, *args],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=timeout,
                          stdin=subprocess.DEVNULL)


# ------------------------------------------------------------------ the door
def test_the_screen_verb_is_registered():
    """An actuator reachable only from Python is one the fleet will not use -- and
    check_wiring.py flagged exactly this module as "built != wired" until the verb landed."""
    r = _run("--help")
    assert "screen" in (r.stdout + r.stderr), "agent_cli has no `screen` verb"


def test_the_three_actions_are_positional_choices_not_subparsers():
    """House convention, and not a style note: the door-parity checker reads add_subparsers as
    separate VERBS, which is how `recall-audit` first arrived as three phantom ones
    (pack/score/recall_audit). `fence` set the convention at agent_cli.py:9213."""
    r = _run("screen", "--help")
    out = r.stdout + r.stderr
    assert "{status,locate,prompt}" in out.replace(" ", ""), out[:400]


def test_status_is_read_only_and_names_what_it_would_refuse():
    """The preflight as a READ. Every refusal the combo can raise should be answerable before a
    caller commits to a sequence, because "why did it refuse" is the question an operator
    actually asks -- and on a locked workstation it is the only question."""
    r = _run("screen", "status", "--json")
    assert r.returncode == 0, r.stderr[:400]
    doc = json.loads(r.stdout)
    for key in ("seat", "uia", "workstation_locked", "foreground_hwnd", "windows", "caps",
                "session_dir", "session_count"):
        assert key in doc, f"status does not report {key!r}"
    assert set(doc["caps"]) >= {"focus", "type", "keys", "invoke"}, doc["caps"]
    for verb, c in doc["caps"].items():
        assert "allowed" in c and "why" in c, (
            f"caps[{verb}] does not say WHY -- a refusal with no remedy is a dead end")


def test_status_does_not_act():
    """A status call must not move the operator's focus. Pinned at the source level because the
    cost of discovering this empirically is the operator losing their window mid-sentence."""
    src = inspect.getsource(C.status)
    for forbidden in ("SendKeys", '"focus"', "'focus'", "SetForegroundWindow", "Click"):
        assert forbidden not in src, (
            f"status() references {forbidden!r} -- a read-only door that focuses or types is "
            f"not read-only")


# ------------------------------------------------------------------ fail-closed
def test_the_combo_refuses_without_the_caps():
    """Measured: `screen status` reported "verbs permitted: NONE" for the super_admin claude
    seat, because the screen tiers are in no role template. The combo must therefore refuse
    end-to-end, not merely log and continue."""
    r = _run("screen", "prompt", "this text must never reach a window", "--json")
    doc = json.loads(r.stdout or "{}")
    assert doc.get("status") == "refused", (
        "the combo did not refuse although the seat holds no screen.* cap: %r" % (doc,))
    assert r.returncode != 0, "a refused combo exited 0"


def test_a_refusal_stops_the_chain_rather_than_continuing():
    """THE COMBO-SPECIFIC PIN. Every step is followed by a return on failure; a chain that
    proceeds past a failed focus types into whatever the operator is looking at."""
    src = inspect.getsource(C.new_session_prompt)
    # every `step(...)` for an acting verb must be followed by a guarded early return
    assert src.count("return stop(") >= 5, (
        "fewer early returns than acting steps -- at least one step can fail and let the chain "
        "continue")
    assert "if not r.ok:" in src, "no step checks its own result"


def test_submit_defaults_to_not_sending():
    """Design step 3 is "Dry actions ... no submit". Submitting is a separate, explicit decision
    and must never be the default of a verb that drives a real desktop."""
    sig = inspect.signature(C.new_session_prompt)
    assert sig.parameters["submit"].default is False
    r = _run("screen", "--help")
    assert "--submit" in (r.stdout + r.stderr), "there is no explicit opt-in to sending"


def test_the_four_outcomes_are_not_a_bool():
    """`staged` (typed, not sent) and `unverified` (sent, read-back blind) are real results that
    a bool rounds to the wrong neighbour in opposite directions."""
    src = inspect.getsource(C)
    for status in ("ok", "staged", "unverified", "refused"):
        assert '"%s"' % status in src, f"the {status!r} outcome does not exist"


# ------------------------------------------------------------------ the receipt plane
def test_the_session_dir_is_derived_not_guessed():
    """This host has SIX project folders (``E--``, ``E--AI-Setup``, ``C--Users-L5``, ...), so a
    slug computed from cwd picks the wrong one. The dir is found by locating our OWN transcript,
    which is the only self-verifying answer to "where will a sibling session land"."""
    src = inspect.getsource(C.session_dir)
    assert "ambient_session_id" in src, (
        "session_dir() does not locate our own transcript; it is guessing the slug")
    d = C.session_dir()
    if d is None:
        pytest.skip("no ~/.claude/projects on this host")
    assert d.is_dir()
    assert (C.projects_root() in d.parents) or d.parent == C.projects_root()


def test_session_files_is_a_snapshot_that_can_detect_a_new_one():
    d = C.session_dir()
    if d is None:
        pytest.skip("no ~/.claude/projects on this host")
    before = C.session_files(d)
    assert isinstance(before, frozenset)
    assert before, "no transcripts found -- the receipt plane would never fire"
    # the receipt is set difference, so a new name must be detectable
    assert (before | {"zzz-not-real.jsonl"}) - before == {"zzz-not-real.jsonl"}


def test_the_nonce_is_embedded_so_the_receipt_is_causal():
    """Without a nonce in the text, "a new session appeared" proves a session appeared -- not
    that it got OUR brief. The nonce is what makes it causal rather than coincident."""
    n = C.make_nonce("some brief")
    assert n and len(n) >= 8
    assert "{nonce}" in C.RECEIPT_TEMPLATE
    assert n in C.RECEIPT_TEMPLATE.format(nonce=n)
    assert C.make_nonce("a") != C.make_nonce("b")


def test_the_centre_strip_is_small_enough_to_be_a_cheap_postcondition():
    """Measured: hashing the whole 8.4M-pixel window costs 88 ms AND changes on any repaint
    anywhere -- a streaming reply alone would trip it every time. A guard that always fires is
    a guard nobody keeps."""
    l, t, w, h = C._centre_strip((-11, -11, 3851, 2171))
    assert w * h <= 200_000, "the post-condition region is too large to be cheap (%dx%d)" % (w, h)
    assert w > 0 and h > 0


def test_text_is_staged_through_the_clipboard_not_through_sendkeys():
    """SendKeys is a little language: ``{}()!+^%`` are syntax and ``{a 3}`` is a repeat count.
    Prose pushed through it does not merely garble, it EXECUTES -- and a brief that arrives
    corrupted is worse than one that never arrives, which is this house's oldest identity law."""
    from core.screenspace import act as A
    src = inspect.getsource(A.act)
    assert "_clip_set" in src, "the type verb does not use the clipboard"
    assert "_escape_sendkeys" in src, (
        "the degraded SendKeys path is unescaped; unescaped prose executes")
    # and the escaper must actually neutralise the dangerous set
    out = A._escape_sendkeys("{a 3} (b) 50% ^x !y +z")
    for ch in "{}()":
        assert ("{%s}" % ch) in out or ("{{}" in out and "{}}" in out), out
    assert "{%}" in out and "{^}" in out and "{!}" in out and "{+}" in out, out


# ------------------------------------------------------------------ the remedy must WORK
def test_the_remedy_restates_existing_caps_rather_than_stripping_them():
    """A remedy that breaks the thing it repairs is worse than no remedy.

    `grant --caps` REPLACES the cap set (core/trust/grant_writer.py: ``eff_caps = caps_from(caps)
    if caps is not None else set(tmpl["caps"])``). So the obvious remedy -- naming only the
    missing cap -- would strip the claude seat's other THIRTEEN, costing it write, exec and
    admin.grant. Measured: claude holds 13 caps as super_admin, so the printed command must name
    17, not 4.
    """
    r = _run("screen", "status", "--json")
    doc = json.loads(r.stdout)
    remedy = doc.get("remedy")
    missing = [v for v, c in doc["caps"].items() if not c["allowed"]]
    if not missing:
        assert remedy is None, "caps are all held but a remedy was printed anyway"
        pytest.skip("the seat already holds every screen tier")
    assert remedy, "verbs are refused but no remedy is offered -- a refusal with no path forward"
    assert "--role" in remedy, (
        "the remedy omits --role, which grant_writer REQUIRES (it raises on an unknown role) -- "
        "following it literally would fail")
    from core.trust import registry
    g = registry.resolve(doc["seat"])
    for held in sorted(c.value for c in g.caps):
        assert held in remedy, (
            f"the remedy does not restate the seat's existing cap {held!r}; running it would "
            f"STRIP that cap, because --caps replaces rather than adds")


def test_the_remedy_names_a_second_party_because_self_grant_is_refused():
    """core/trust/grant_writer.py raises PermissionError when agent_id == by: "a second party
    mints your authority". A remedy that reads as something the seat can run on itself sends the
    reader into a guard, and worse, implies an actuator could self-authorise onto the desktop."""
    r = _run("screen", "status", "--json")
    doc = json.loads(r.stdout)
    remedy = doc.get("remedy")
    if not remedy:
        pytest.skip("nothing missing")
    low = remedy.lower()
    assert "second party" in low or "--by daniil" in low, (
        "the remedy does not say who may run it; self-granting raises PermissionError")
    assert "--hours" in remedy or "--permanent" in remedy, (
        "the remedy is not time-boxed, and grant_writer refuses an untimed, non-permanent grant")


def test_the_remedy_withholds_the_tiers_no_verb_needs():
    """screen.launch and screen.privileged map to NO verb (act.VERB_CAPS), and the design
    reserves privileged for authenticated daniil. A remedy should grant what is needed and not a
    tier more -- over-granting is how a time-boxed drill becomes standing desktop control."""
    r = _run("screen", "status", "--json")
    doc = json.loads(r.stdout)
    remedy = doc.get("remedy") or ""
    if not remedy:
        pytest.skip("nothing missing")
    assert "screen.privileged" not in remedy, "the remedy grants the privileged tier"
    assert "screen.launch" not in remedy, "the remedy grants a tier no verb uses"


# ------------------------------------------------------------------ read before you paste
def test_show_prints_the_brief_without_touching_the_desktop():
    """`--show` is the only way to READ what the verb would send. It matters because assembling
    the brief is not transparent: `--handoff` resolves a spilled note, so the text that would go
    out is not always the text a caller thinks they assembled -- and the brief is the one artifact
    here that nothing downstream can validate."""
    r = _run("screen", "prompt", "hello world", "--show", "--json")
    assert r.returncode == 0, r.stderr[:300]
    doc = json.loads(r.stdout)
    assert doc["text"].startswith("hello world")
    assert doc["nonce"] and doc["nonce"] in doc["text"], "the receipt nonce is not in the brief"
    assert doc["chars"] == len(doc["text"])


def test_show_does_not_act_even_when_submit_is_also_passed():
    """`--show --submit` must still send nothing. A preview flag that defers to a send flag is a
    preview that sometimes publishes, which is the worst of both."""
    r = _run("screen", "prompt", "must never be sent", "--show", "--submit")
    assert r.returncode == 0, r.stderr[:300]
    assert "NOTHING SENT" in r.stdout, r.stdout[:300]
    # and no refusal chain ran at all -- it returned before preflight
    assert "preflight" not in r.stdout


def test_a_spilled_handoff_note_is_inlined_rather_than_left_as_a_pointer():
    """`handoff` caps its --note at 1000 chars and spills the rest to a durable note, leaving a
    retrieval command behind. That is right for a field a seat reads at BOOT and wrong for text
    PASTED into a fresh session: the substance would be one command away, which is exactly the
    hop this verb exists to remove.

    Pinned because the first implementation failed SILENTLY. Notes are stored ADR-shaped
    (id/title/status/context/decision/...), so reading `body` or `content` -- the names a reader
    naturally reaches for -- returned nothing and fell back to the pointer, with no error. The
    brief looked plausible and was truncated at its opening.

    THE DELIVERY IS DETERMINISTIC, THE LEDGER IS NOT, so this pins the resolver rather than a
    live lookup. `_consumed()` (core/context/briefing_loader.py:15) retires a handoff as soon as
    the target records ANY lesson newer than it -- and BOTH Vandor seats run under the agent id
    `claude`, so the sibling seat's lessons retire handoffs addressed to me. Measured tonight:
    `load_briefing_from_previous_handoff("claude")` returned FOUND and then, seconds later,
    None, with no handoff written or consumed by me in between. A pin that asserted through the
    live ledger would pass or skip according to another seat's unrelated activity.
    """
    import agent_cli  # noqa: PLC0415 -- the resolver lives on the CLI door
    assert hasattr(agent_cli, "_resolve_handoff_spill")
    src = inspect.getsource(agent_cli._resolve_handoff_spill)
    assert '"decision"' in src, (
        "the resolver does not read the `decision` attribute. Notes are stored ADR-shaped "
        "(id/title/status/context/decision/rationale/...), so reading `body` or `content` -- the "
        "names a reader naturally reaches for -- returns nothing and falls back to the POINTER "
        "with no error. That is how the first implementation shipped a brief truncated at its "
        "opening while looking entirely plausible.")
    assert src.index('"decision"') < min([src.index('"body"'), src.index('"content"')]), (
        "`decision` must be tried FIRST; the others are fallbacks for differently-shaped records")
    # and the renderer must actually route the context field through it
    rsrc = inspect.getsource(agent_cli._latest_handoff_text)
    assert "_resolve_handoff_spill" in rsrc, (
        "the brief renderer never calls the resolver, so a spilled note stays a pointer")

    # Opportunistic: if a handoff IS live right now, the end-to-end result must be pointer-free.
    r = _run("screen", "prompt", "--handoff", "claude", "--show", "--json")
    if r.returncode == 0:
        doc = json.loads(r.stdout)
        assert "handoff-spill:" not in doc["text"], (
            "the brief carries a spill POINTER instead of the spilled body -- the new session "
            "would have to go fetch its own briefing")
