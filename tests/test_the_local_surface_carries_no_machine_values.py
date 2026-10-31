"""Pins for the LOCAL surface of the purity ratchet (amendment A1, 2026-10-31).

WHAT THIS DEFENDS. `local/`, `arsenal/panel/` and `scripts/phone/` are committed to a PUBLIC repo,
so they may carry this deployment's SHAPE and never this machine's ADDRESS or a home path. The
pre-push scan that found a real tailnet address (RFC 6598 band; the value itself is withheld here,
which is the point of the file) and an absolute home path headed for the public remote found them
by luck -- someone happened to run the scan. This is the gate that finds them every time, and, per
the ratchet's three rules, a gate whose baseline can go missing must REFUSE rather than pass,
because a fresh clone with no baseline is exactly the deployment it is meant to guard.

NOTE ON THE VECTORS BELOW: every address in this file is a TEXTBOOK example (the RFC 6598 CGNAT
band, 192.168.0.x, 10.1.2.3) and every home path names `someone`. That is not decoration -- the
first draft of this file quoted the REAL tailnet address in its own docstring, and a pre-push scan
of the branch caught it: the test written to forbid a machine value had put one in the public repo.
Placeholders are how a gate documents what it refuses without being an instance of it.

The pins come in three kinds, deliberately:
  * the SHIPPED TREE is at zero (the honest freeze);
  * each CLASS actually bites a planted value (a regex that matches nothing is decoration);
  * the GATE refuses, fails and reports correctly, drilled through the checker's own functions --
    never by putting a fake secret into the real tree.

Run: py tests/test_the_local_surface_carries_no_machine_values.py   (or via pytest)
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_core_purity as purity                              # noqa: E402

BASELINE = purity.LOCAL_BASELINE_PATH


# ------------------------------------------------------------------ 1. the shipped tree is at zero
def test_the_shipped_local_surface_carries_no_machine_values():
    found = purity.measure_local(ROOT)
    assert found == {}, (
        "MACHINE VALUES in the public local/panel surface: {}. A tailnet address is a routable "
        "address for one machine and a home path names an account: both belong in the private "
        "profile (akashic-local/profile/), read through core/local.py's overlay -- leave a null or "
        "a ${{INSTANCE_ROOT}} derivation here.".format(
            {k: v for k, v in found.items()}))


def test_the_baseline_is_committed_and_frozen_at_zero():
    assert os.path.isfile(BASELINE), (
        "the local-surface baseline is missing. The gate REFUSES in that state (which is correct), "
        "but a tree whose baseline is untracked has a ratchet only on one workstation")
    with open(BASELINE, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["total"] == 0, (
        f"the freeze is {doc['total']}, not zero. A non-zero local-surface baseline is a machine "
        f"value this repo already ships: {doc['files']}")
    assert doc["files"] == {}
    assert set(doc["_scope"]["dirs"]) == {"local", "arsenal/panel", "scripts/phone"}, (
        "the governed scope changed. Narrowing it is how a gate stops covering the thing that "
        "leaked; if a directory really left the surface, say so in the commit.")


# ---------------------------------------------------------------------- 2. each class actually bites
@pytest.mark.parametrize("text,cls", [
    ("host: 100.64.9.9", "tailnet"),
    ("host = '100.64.0.1'", "tailnet"),                 # the generic CGNAT example, still caught
    ("host: 192.168.0.10", "lan"),
    ("host: 10.1.2.3", "lan"),
    ("host: 172.20.0.5", "lan"),
    ('"path": "C:\\\\Users\\\\someone\\\\AppData"', "home"),
    ('"path": "C:/Users/someone/dev"', "home"),
    ('"path": "/home/someone/tool"', "home"),
    ('"path": "/Users/someone/tool"', "home"),
])
def test_each_machine_value_class_is_counted(text, cls):
    counts = purity.count_machine(text)
    assert counts[cls] >= 1, f"{cls} class did not match {text!r}: {counts}"


@pytest.mark.parametrize("text", [
    "127.0.0.1:8796",                    # loopback is the panel's whole job
    "${INSTANCE_ROOT}/.claude/x",        # a DERIVATION, which is what belongs here
    "~/dev/openrgb-1.1",                 # home-relative, not a home path
    "$env:USERPROFILE\\.ssh\\config",
    "1000.1.2.3",                        # not an address
    "172.15.0.1",                        # just outside the RFC1918 172.16/12 block
])
def test_ordinary_local_values_are_NOT_flagged(text):
    assert purity.total_of(purity.count_machine(text), purity.MACHINE_CLASSES) == 0, (
        f"{text!r} was flagged; a gate that cries wolf on loopback and derivations is a gate "
        f"someone switches off")


# ---------------------------------------------------------------------------- 3. the gate's behaviour
def test_a_missing_baseline_REFUSES_rather_than_passing(tmp_path):
    """Exit 2, not 1 and not 0: 'I cannot answer' is a third answer, and collapsing it into a pass
    is the invisible-absence shape both baselines exist to prevent."""
    with pytest.raises(SystemExit) as exc:
        purity.load_baseline(str(tmp_path / "absent.json"), label="local-surface")
    assert exc.value.code == 2


def test_the_gate_FAILS_on_a_planted_value_in_a_throwaway_tree(tmp_path):
    """Pure drill: a fake instance root, never the real tree."""
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "reachability.json").write_text(
        json.dumps({"version": 1, "phone": {"tailnet_host": "100.64.9.9"}}), encoding="utf-8")
    (tmp_path / "arsenal" / "panel").mkdir(parents=True)
    (tmp_path / "arsenal" / "panel" / "app.js").write_text(
        "const HOME = 'C:/Users/someone/x';\n", encoding="utf-8")
    current = purity.measure_local(tmp_path)
    assert set(current) == {"local/reachability.json", "arsenal/panel/app.js"}, current

    with open(BASELINE, encoding="utf-8") as fh:
        baseline = json.load(fh)
    failures, drops, new = purity.compare(current, baseline, purity.MACHINE_CLASSES, "machine-value")
    assert failures, f"the ratchet did not fire on a bare tailnet address: {drops} {new}"
    assert any("rose" in detail for _k, detail in failures), failures


def test_the_local_half_of_the_gate_is_green_through_its_own_cli(monkeypatch):
    """End-to-end through the CLI, on THIS surface only.

    Deliberately not `main([]) == 0`: the default run grades both surfaces, and the Core half
    carries debt that belongs to `core/comm/discord_inbound.py` (a seat roster and prose literals
    landed at 7a9b2b950 without re-freezing the Core baseline). A pin here that went red for that
    reason would point at the wrong file and hold this surface hostage to another slice's debt.
    The Core half is graded by its own gate and its own baseline.
    """
    monkeypatch.setenv("PURITY_SURFACE", "local")
    assert purity.main([]) == 0


# ------------------------------------------------------------------- 4. the profile is what fills it in
def test_the_public_files_keep_nulls_where_the_private_profile_speaks():
    """The split, stated as data: these keys are `null` here BY DESIGN, and core/local.py's overlay
    is the only thing that may fill them."""
    with open(os.path.join(ROOT, "local", "phone-panel.json"), encoding="utf-8") as fh:
        panel = json.load(fh)
    assert panel["panel"]["agent"] is None, (
        "which seat the panel reports on is a MACHINE value; it belongs in "
        "akashic-local/profile/phone-panel.json")
    with open(os.path.join(ROOT, "local", "reachability.json"), encoding="utf-8") as fh:
        reach = json.load(fh)
    assert reach["phone"]["tailnet_host"] is None
    assert reach["phone"]["watcher"] is None
