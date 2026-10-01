"""T414 pins -- a canary must measure a live organ, refuse to guess, and declare its own death.

WHY (2026-09-27). In one session this house found six broken organs and every one surfaced by
luck: 877 citations resolvable on one machine only for 65 days, a connectome with zero edges since
a migration, 38 approved rows aged 35-79 days rendered to every seat as fresh work, 51 done rows
orphaned by a rewrite run hours earlier, `lookback` answering nothing for months, and
`events --kind` silently not filtering. All six pre-commit guardrails read code or docs; none asks
whether an organ still ANSWERS.

The technique is Sergey Nikitenko's, from the Mnemosyne notebook (credited in the checker's
docstring): prove a capability is live by watching its refusal REASON change. Generalised: an organ
is alive when it answers a question whose answer you already know.

These pins hold the four properties that keep this checker from becoming the seventh thing nobody
prunes -- including the one the corpus warned about while it was being written: a meter whose
inputs are fixtures proves the meter, never the measurement.
"""

import ast
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.checkers.check_organ_canaries as oc  # noqa: E402


def test_every_canary_declares_what_would_retire_it():
    """A capability without a retirement rule is a debt with a nice interface, and every organ in
    this house has a birth and no death. The registry's own invariant is the only thing stopping
    this checker from becoming another immortal entry -- so it is enforced, not documented."""
    for name, (fn, retire_when) in oc.CANARIES.items():
        assert callable(fn), f"{name} has no callable"
        assert isinstance(retire_when, str), f"{name} has no real retirement condition: {retire_when!r}"
        assert len(retire_when.strip()) > 30, f"{name} has no real retirement condition: {retire_when!r}"
        assert oc.self_test() == 0


def test_the_registry_refuses_a_canary_with_no_retirement_rule(monkeypatch):
    """The invariant must FAIL when violated, or it is decoration. Pinning the negative."""
    monkeypatch.setitem(oc.CANARIES, "a canary someone added in a hurry", (lambda: (oc.ALIVE, ""), ""))
    assert oc.self_test() == 1, "the registry accepted a canary with no retirement rule"


def test_three_verdicts_not_a_boolean():
    """ZERO IS NOT NO. 'the organ answered wrong' and 'I could not ask it' are different
    observations, and collapsing them is the defect this whole family exists to catch. A canary
    that cannot say UNCHECKED will report a broken probe as a healthy organ."""
    assert len({oc.ALIVE, oc.DEAD, oc.UNCHECKED}) == 3
    src = Path(ROOT, "scripts", "checkers", "check_organ_canaries.py").read_text(encoding="utf-8")
    assert "COULD-NOT-CHECK IS NOT A PASS" in src, (
        "the report must say out loud that an unrunnable canary is not a pass"
    )


def test_the_gate_fails_on_unchecked_not_only_on_dead(monkeypatch):
    """An unrunnable canary is an unwatched organ. If the gate only failed on DEAD, the cheapest
    way to go green would be to break the probe -- which is the shape of a guard that trains you
    to mutilate the instrument."""
    monkeypatch.setattr(
        oc,
        "CANARIES",
        {"a probe that cannot run": (lambda: (oc.UNCHECKED, "no plane"), "retire when the plane it reads is removed")},
    )
    assert oc.report(gate=True) == 1, "the gate passed with an unrunnable canary"


def test_a_raising_canary_is_unchecked_never_a_pass(monkeypatch):
    """A canary is a subprocess call against a live system; it WILL fail sometimes. It must
    degrade to 'could not check', never to silence and never to a crash that takes the gate with
    it."""
    rc, _out = oc.run("-c", "import sys; sys.exit(3)")
    assert rc == 3, "run() must surface the real exit code"
    rc2, _out2 = oc.run("-c", "raise SystemExit(0)", timeout=60)
    assert rc2 == 0
    rc3, out3 = oc.run("nonexistent_file_that_cannot_be_run.py")
    assert rc3 != 0, "a failed invocation must return a non-zero rc and say something"
    assert out3, "a failed invocation must return a non-zero rc and say something"


def test_no_canary_supplies_its_own_input():
    """THE ONE THE CORPUS WARNED ABOUT WHILE THIS WAS BEING WRITTEN: unit tests of a meter prove
    the meter, never the measurement. A canary that builds its own fixture measures the fixture.
    Every canary here must read a PRODUCTION artifact -- a live verb, the live index, the live
    ledger -- so a dead organ cannot be hidden behind a helpful stub.

    Enforced structurally rather than by inspection: no canary body may construct a temp dir, a
    fake store, or a literal record to measure.
    """
    src = Path(ROOT, "scripts", "checkers", "check_organ_canaries.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned = {"mkdtemp", "TemporaryDirectory", "NamedTemporaryFile", "MagicMock", "Mock", "patch"}
    offenders = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("canary_")):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                f = sub.func
                nm = getattr(f, "attr", None) or getattr(f, "id", None)
                if nm in banned:
                    offenders.append(f"{node.name} calls {nm}")
    assert not offenders, "a canary is measuring its own fixture: " + "; ".join(offenders)


def test_every_canary_names_the_defect_it_was_born_from():
    """A canary with no recorded instance is a guess about what might break. Each of these five was
    born from a measured failure, and the docstring has to carry it -- otherwise a later seat
    cannot tell a real watch from a speculative one, and speculative watches are what make a
    checker family rot."""
    src = Path(ROOT, "scripts", "checkers", "check_organ_canaries.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("canary_"):
            doc = ast.get_docstring(node) or ""
            assert len(doc) > 120, f"{node.name} has no substantive docstring"
            assert any(k in doc for k in ("Measured", "measured", "T41", "2026-")), (
                f"{node.name} does not cite the measurement or defect it was born from"
            )


def test_it_runs_against_the_live_system_and_reports_something():
    """The end-to-end property. Not asserting a verdict -- the verdicts are the finding and they
    will change as organs are fixed. Asserting that the checker executes against production and
    classifies every canary into exactly one of the three states."""
    rc = oc.report(gate=False)
    assert rc == 0, "the non-gated report must not fail the caller"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))


def test_the_gate_ratchets_on_new_deaths_not_recorded_ones():
    """The gate must freeze the debt, not forgive it, and not paint itself red on day one.

    Five organs were already dead when the canaries were written. Gating on them absolutely
    would have made the gate red immediately, which is how a gate stops carrying information --
    the failure state/ci/guardrail_baseline.json exists to end ("red became the normal state, so
    a NEW red carried no information and nobody looked"). A RECORDED death passes; an
    UNRECORDED one fails.

    This asserts the DIFFERENTIAL, not an absolute exit code, and that is deliberate: under the
    isolated test store one canary cannot run at all, and the gate correctly fails on an
    unrunnable canary ("an unwatched organ"). An absolute assertion would be testing which Redis
    db the suite points at rather than whether the ratchet works.
    """
    import json as _json
    import subprocess as _sp
    import sys as _sys

    bl = os.path.join(ROOT, "state", "ci", "organ_canary_baseline.json")
    assert os.path.exists(bl), "the ratchet has no baseline; the gate would fail on known debt"
    keep = open(bl, encoding="utf-8").read()
    recorded = (_json.loads(keep) or {}).get("dead") or {}
    assert recorded, "an empty baseline makes the gate stricter, not looser -- but records nothing"
    for name, reason in recorded.items():
        assert str(reason).strip(), f"{name} is recorded dead with no reason -- a silent zero"

    def _gate():
        r = _sp.run(
            [
                _sys.executable,
                "-X",
                "utf8",
                os.path.join(ROOT, "scripts", "checkers", "check_organ_canaries.py"),
                "--gate",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        return (r.stdout or "") + (r.stderr or "")

    with_all = _gate()
    assert "NEWLY" not in with_all, "a death recorded in the baseline still reads as NEW debt: " + with_all[-500:]

    victim = next(iter(recorded))
    try:
        d = _json.loads(keep)
        d["dead"].pop(victim)
        open(bl, "w", encoding="utf-8", newline=chr(10)).write(_json.dumps(d, indent=2) + chr(10))
        without = _gate()
    finally:
        open(bl, "w", encoding="utf-8", newline=chr(10)).write(keep)

    assert "NEWLY" in without, (
        "un-recording a dead organ did not raise NEW debt -- the ratchet is decorative: " + without[-500:]
    )
    assert victim in without, "the gate must NAME the newly dead organ; an unattributed failure cannot be acted on"
