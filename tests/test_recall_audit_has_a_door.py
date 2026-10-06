"""RED pins: the instrument that measures whether recall is ACCURATE has no door.

PRE-REGISTRATION (M3). RED at this commit; the verb follows separately.

DANIEL, going to sleep 2026-10-06: "work on the ergonomics and reachibility of memory. so that
the right memory reaches us at the right moment."

WHAT IS ACTUALLY BROKEN, measured by Navi tonight in a sealed fence half ([CERTAIN], her
re-derivation, not a claim of mine):

    629 injections / 988,282 chars / 1,157 DISTINCT lessons / 2 flips / 1 credited
    => ~988,000 characters of injected memory to credit ONE lesson.

Her reading: "the session read almost the whole corpus and found one of it useful. That is not
a targeting miss; that is the corpus answering 'nothing here helps' 1,156 times at full
injection cost."

AND WE CANNOT ACT ON THAT, because we have never measured the thing it implies.
`core/recall/precision_audit.py` says so in its own docstring, quoting kimi from 2026-07-27:

    "We have never demonstrated a ranking failure BECAUSE WE HAVE NEVER MEASURED RANKING. The
     only instrument we built this arc was a membership census, so the only failures it COULD
     find were selection-shaped. Finding selection failures under a selection streetlight does
     not make selection the constraint; it makes it the only place we looked."

THE MODULE IS BUILT, TESTED, AND HAS NO DOOR. Measured tonight:
  - `harvest()` returns **1,564 impressions** right now. The corpus already exists -- the hook
    has been writing {"t": target, "s": [sources]} per firing all along, and the module's own
    docstring says it "just had no reader".
  - `sample()` is seed-deterministic, `render_pack()` renders a correct BLIND pack, `score()`
    computes precision + recall + agreement and returns STARVED when nothing is labelled.
  - `tests/test_precision_audit.py` exercises all four functions.
  - `scripts/checkers/check_wiring.py:179` carries an EXPLICIT EXCEPTION for it:
        "core/recall/precision_audit.py": "built-ahead (52db9b5): the retrieval-accuracy
         instrument ..."

So the house KNOWS it is unwired and granted it a pass. That pass is why it has never run. This
is `capability_without_a_door` -- "when adding a capability to a lower layer, expose it on the
SAME door agents already use, in the same slice, or it stays dead" -- and it has stayed dead
for the one instrument that could tell us whether the 988k number is a ranking failure or a
selection failure. Those have OPPOSITE fixes, and we have been arguing about which without the
number.

WHY A VERB AND NOT A SCRIPT. `score()` takes labels from MULTIPLE labellers and reports their
agreement; `render_pack()` is deliberately blind so a labeller cannot read the ranker's prior
opinion back to it. That shape wants a fleet: three seats labelling the same blind pack is
N-version blind review, which is this house's standing method. A door is what lets a peer
labeller participate without being handed a Python call.

Run::

    py -m pytest tests/test_recall_audit_has_a_door.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLI = str(ROOT / "agent_cli.py")


def _run(*args, timeout=180):
    return subprocess.run([sys.executable, "-X", "utf8", CLI, *args],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=timeout,
                          stdin=subprocess.DEVNULL)


# ----------------------------------------------------------------- the door exists at all
def test_the_verb_is_registered():
    """THE PIN. An instrument reachable only by importing Python is an instrument that does
    not run -- which is the measured history of this one."""
    r = _run("--help")
    assert "recall-audit" in (r.stdout + r.stderr), (
        "agent_cli has no `recall-audit` verb. core/recall/precision_audit.py is built, "
        "tested, holds 1,564 harvested impressions, and has an explicit unwired exception at "
        "scripts/checkers/check_wiring.py:179 -- which is exactly why it has never been run.")


def test_pack_renders_a_blind_labelling_pack():
    """The harvest->sample->render half must work from the door, with a deterministic seed so
    a published number can be re-drawn (the module's own words: "a published number that
    cannot be re-drawn cannot be audited")."""
    r = _run("recall-audit", "pack", "--n", "3", "--seed", "1")
    assert r.returncode == 0, f"pack failed rc={r.returncode}: {r.stderr[:400]}"
    out = r.stdout
    assert "PRECISION AUDIT" in out.upper(), out[:300]
    assert "ACTION:" in out, "the pack does not show the action each item was judged against"
    assert "case 1" in out.lower(), out[:300]


def test_the_pack_is_blind_by_construction():
    """RATCHET ON THE INSTRUMENT'S OWN LAW. render_pack deliberately omits usefulness counters,
    credit history and seat identity, because "a labeller who can see that a lesson has
    'helped 4x' is not judging relevance -- they are reading the ranker's prior opinion back to
    it, and the audit would measure our own agreement with ourselves."

    A door that helpfully enriches the pack would destroy exactly that property, so the pin
    lives here rather than only in the module.
    """
    r = _run("recall-audit", "pack", "--n", "5", "--seed", "1")
    assert r.returncode == 0, r.stderr[:300]
    low = r.stdout.lower()
    for leak in ("helped", "useful=", "votes", "credited", "noise="):
        assert leak not in low, (
            "the pack leaks the ranker's prior opinion (%r) -- a labeller reading it is "
            "measuring our agreement with ourselves, not relevance" % leak)


def test_the_same_seed_draws_the_same_sample():
    """Re-drawable, or the number cannot be audited."""
    a = _run("recall-audit", "pack", "--n", "4", "--seed", "7")
    b = _run("recall-audit", "pack", "--n", "4", "--seed", "7")
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout, "same seed drew a different sample -- the audit is not re-drawable"


# ----------------------------------------------------------------- the scoring half
def test_score_with_no_labels_CONFESSES_rather_than_returning_zero():
    """THE CONFIDENT-ZERO PIN, and it is the module's own stated law: an unlabelled audit
    "measured nothing, which is a confession, not a score". A door that rendered that as
    precision 0.0 would manufacture the exact false number the instrument exists to prevent.
    """
    r = _run("recall-audit", "score", "--labels", "{}", "--json")
    assert r.returncode == 0, r.stderr[:300]
    doc = json.loads(r.stdout)
    assert doc.get("status") == "STARVED", (
        "an audit with no labels did not report STARVED: %r" % (doc.get("status"),))
    assert doc.get("precision") is None, (
        "precision rendered as %r for zero labelled observations -- that is a manufactured "
        "number" % (doc.get("precision"),))


def test_score_reports_agreement_across_labellers():
    """The fleet shape. Two labellers disagreeing on an item must surface as DISPUTED rather
    than being averaged into a number that hides it -- N-version blind review only pays if the
    disagreement survives to the reader."""
    labels = json.dumps({
        "alice": {"1:a": "on", "1:b": "off"},
        "bob":   {"1:a": "off", "1:b": "off"},
    })
    r = _run("recall-audit", "score", "--labels", labels, "--json")
    assert r.returncode == 0, r.stderr[:300]
    doc = json.loads(r.stdout)
    assert doc.get("status") != "STARVED", doc
    assert doc.get("agreement") is not None, "agreement not reported across two labellers"
    assert "1:a" in json.dumps(doc.get("disputed") or []), (
        "the item the two labellers disagreed on is not listed as disputed: %r" % (doc,))
