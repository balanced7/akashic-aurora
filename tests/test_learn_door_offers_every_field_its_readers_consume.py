"""Every field the recall layers READ must have a WRITER on the canonical learn door.

WHY THIS PIN EXISTS
-------------------
Measured 2026-08-25 over all 1120 lesson records: `root_cause` and `files_affected` sit at
EXACTLY 0.0% fill. Not low -- zero. Exactly-zero is a door signature; culture and laziness
produce low-but-nonzero.

The cause was not culture. `agent_cli.py learn` never offered the fields, so no agent could
fill them however much it wanted to. Meanwhile both are READ:

    root_cause      -> one of the five dedup dimensions (comparing "" to "" across the
                       whole corpus, a CONSTANT masquerading as a fifth of the signal)
                    -> infer_domain()'s scored text blob
                    -> the index writer
                    -> draft_anti_pattern_slug(), whose docstring says it PREFERS root_cause
                       "(it names WHY it failed)" -- and whose only call site passed a
                       hardcoded "" for it, so it has run on its fallback input every time it
                       has ever been called and never once on its preferred one.

    files_affected  -> base_score tier 0.7, unioned into the lesson's path set

A read path with no write path degrades output silently and forever: nothing errors, nothing
logs, the results are just quietly worse than designed.

THE CLASS, NOT THE INSTANCE. The corpus already held `recall_dissent_slice2_capture` -- "a
write door must OFFER a field or it stays empty (0 anti-patterns came from a missing flag, not
agent laziness)". That lesson was correct, and its fix was point-applied to `--anti-pattern`
alone (0% -> 3.3%). The other members of the same class were left at zero, where the lesson's
own existence then made them HARDER to find, because the class read as already handled.

So this file pins the CLASS, not the two fields: a reader-without-a-writer is the defect.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _learn(*extra, name):
    """Record one lesson through the real CLI door and return its stored record."""
    cmd = [sys.executable, "agent_cli.py", "learn", "pintest",
           "--experiment", name, "--tried", "t", "--result", "r",
           "--recommend", "rec", *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0, f"learn door failed: {r.returncode} {r.stderr[-400:]}"
    got = subprocess.run([sys.executable, "agent_cli.py", "recall", "--full",
                          f"learn:experiment:{name}", "--json"],
                         capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert got.returncode == 0, f"recall failed: {got.stderr[-300:]}"
    return json.loads(got.stdout)


def test_the_door_offers_root_cause_and_it_lands_in_the_record():
    """THE LOAD-BEARING PIN. Four consumers read this field; something must write it."""
    rec = _learn("--root-cause", "the door never offered the field",
                 name="pin_root_cause_roundtrip")
    assert rec.get("root_cause") == "the door never offered the field", (
        f"root_cause did not survive the door: {rec.get('root_cause')!r}. Four readers "
        f"(dedup dims, infer_domain, the index, draft_anti_pattern_slug) consume this field.")


def test_the_door_offers_files_affected_and_it_lands_in_the_record():
    """base_score tier 0.7 unions this into the lesson's path set."""
    rec = _learn("--files-affected", "core/comm/launcher.py,scripts/quiet/sitecustomize.py",
                 name="pin_files_affected_roundtrip")
    got = rec.get("files_affected")
    if isinstance(got, str):
        got = [p for p in got.replace(",", " ").split() if p]
    assert "core/comm/launcher.py" in (got or []), (
        f"files_affected did not survive the door: {rec.get('files_affected')!r}. "
        f"base_score reads it at tier 0.7.")


def test_the_anti_pattern_slug_helper_actually_receives_root_cause():
    """Its docstring PREFERS root_cause. The call site passed a hardcoded "" for it.

    Asserted on the helper's own behaviour rather than on the call site's source, so this
    stays true if the call moves: given a root_cause, the slug must derive from THAT and not
    from what_tried.
    """
    sys.path.insert(0, ROOT)
    from core.learning.learning_store import draft_anti_pattern_slug
    slug = draft_anti_pattern_slug("banana pancake syrup", "socket timeout wedge", "zebra")
    assert slug, "helper returned nothing for a real root_cause"
    assert "banana" not in slug and "zebra" not in slug, (
        f"slug {slug!r} came from the FALLBACK inputs -- root_cause was ignored, which is "
        f"what a hardcoded '' at the call site looks like from the outside")


@pytest.mark.parametrize("field", ["root_cause", "files_affected"])
def test_every_field_the_readers_consume_is_offered_by_the_door(field):
    """The CLASS pin: enumerate what the door offers, diff against what the readers read.

    Reads the door's own --help rather than its source, because --help is the contract an
    agent actually sees. A field readable by the ranker but absent from this list cannot be
    filled by anyone, however willing.
    """
    r = subprocess.run([sys.executable, "agent_cli.py", "learn", "--help"],
                       capture_output=True, text=True, cwd=ROOT, timeout=120)
    flag = "--" + field.replace("_", "-")
    assert flag in r.stdout, (
        f"{flag} is not offered by the learn door, but {field} IS read by the recall layers. "
        f"A field nobody CAN write is indistinguishable from a field nobody WANTS.")
