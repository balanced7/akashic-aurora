"""RED pins: the TOKENS TODAY gauge reads two keys that nothing writes, and renders the miss as 0.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

W118, filed against a gauge that is lying RIGHT NOW. Measured 2026-10-07 from the live tree:

    state/runner_deepseek_2026-10-07.json
        prompt_tokens      5031502
        completion_tokens    17654
        total_tokens       5049156

    core.comm.engine_vitals._today_journal("deepseek", None)
        {'prompt': 0, 'completion': 0}

Five million tokens rendered as zero. The cause is two words, at engine_vitals.py:62::

    return {"prompt": int(d.get("prompt") or 0), "completion": int(d.get("completion") or 0)}

The journal writes ``prompt_tokens`` and ``completion_tokens`` (scripts/runner_token_journal.py:98-99
names the accumulators, and the serialized file above proves the keys). The gauge asks for ``prompt``
and ``completion``. Neither key exists at the top level, ``.get`` returns None, ``or 0`` turns that
into a number, and a reader sees a confident zero.

THE TWO FAILURES ARE SEPARABLE AND BOTH MATTER.

1. THE KEY MISMATCH. A plain bug: fix the names and 5,049,156 tokens appear.

2. ``or 0`` IS THE DESIGN DEFECT, and it is the one worth pinning. A missing key and a genuinely
   idle day are not the same fact, and this function renders them identically. That is the typed-
   absence rule this house keeps paying to re-learn: an unmeasurable quantity must read UNKNOWN,
   never 0, because 0 is a measurement. It is the same shape as ``never_report_a_rate_without_the
   _quantity_that_bounds_it`` ("render an unmeasurable rate as UNCHECKABLE, never 0.0 -- over an
   empty denominator, zero reads as the most alarming possible finding") and the same shape as the
   corpus report that counted survivors. Here zero reads as the most REASSURING possible finding,
   which is worse: nobody investigates a quiet meter.

   And the mismatch hid behind exactly that. A gauge that said UNKNOWN on 2026-08-07, when W118 was
   filed, would have been fixed that day. Saying 0 bought it two months.

NOT A HYPOTHETICAL BUDGET CONCERN: the same journal carries ``cost_est`` and the fleet prices turns
from it, so a gauge that reads zero prompt tokens is the visible half of a meter the operator uses
to decide what a seat may spend.

Run::

    py -m pytest tests/test_the_token_gauge_reads_the_keys_the_journal_writes.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: The keys the writer actually serializes. Taken from a real file on 2026-10-07, not from the
#: writer's attribute names -- an attribute is not a key and conflating them is how this started.
WRITER_KEYS = ("prompt_tokens", "completion_tokens")


def _journal(tmp_path, **fields) -> str:
    """Write a journal in the REAL shape and return its directory."""
    import time
    p = tmp_path / ("runner_probe_%s.json" % time.strftime("%Y-%m-%d"))
    body = {"agent": "probe", "turns": 1}
    body.update(fields)
    p.write_text(json.dumps(body), encoding="utf-8")
    return str(tmp_path)


# ------------------------------------------------------------------ the defect
def test_the_gauge_reads_a_journal_the_writer_actually_produced(tmp_path):
    """THE PIN. Round-trip: write the real shape, read it back through the gauge.

    This is deliberately a round trip rather than an assertion about key names. A test that checks
    the reader uses the string "prompt_tokens" passes the moment someone edits the reader, even if
    the writer has moved on again. Only writing and reading proves they agree.
    """
    from core.comm import engine_vitals as ev
    d = _journal(tmp_path, prompt_tokens=5031502, completion_tokens=17654, total_tokens=5049156)
    got = ev._today_journal("probe", d)
    assert got.get("prompt") == 5031502 and got.get("completion") == 17654, (
        "the gauge read %r from a journal holding prompt_tokens=5031502, completion_tokens=17654. "
        "engine_vitals.py:62 asks for d['prompt'] and d['completion']; the writer serializes "
        "prompt_tokens and completion_tokens (verified against "
        "state/runner_deepseek_2026-10-07.json on 2026-10-07, where the live gauge reported "
        "{'prompt': 0, 'completion': 0} over 5,049,156 real tokens)." % (got,))


def test_an_unreadable_journal_is_not_reported_as_zero(tmp_path):
    """THE PIN THAT MATTERS. A missing measurement and a measured zero are different facts.

    `or 0` collapses them, and a quiet meter is the one nobody investigates -- which is precisely
    how a two-word key mismatch survived from 2026-08-07 to 2026-10-07 while the number it reported
    was wrong every single day.
    """
    from core.comm import engine_vitals as ev
    missing = ev._today_journal("no-such-agent-at-all", str(tmp_path))
    assert missing.get("prompt") is None or missing.get("unknown") or missing.get("measured") is False, (
        "a journal that does not exist reports %r -- indistinguishable from a seat that ran all day "
        "and spent nothing. An unmeasurable quantity must say so; 0 is a measurement." % (missing,))


def test_a_genuine_zero_is_still_reported_as_zero(tmp_path):
    """The other half of the same rule, and the reason the fix cannot just be `return None`.
    A journal that EXISTS and records no tokens is a real measurement of zero and must stay 0."""
    from core.comm import engine_vitals as ev
    d = _journal(tmp_path, prompt_tokens=0, completion_tokens=0, total_tokens=0)
    got = ev._today_journal("probe", d)
    assert got.get("prompt") == 0 and got.get("completion") == 0, (
        "a journal recording a real zero reported %r; measured-zero must survive the fix" % (got,))


# ------------------------------------------------------------------ ratchets
def test_the_writer_still_serializes_the_keys_this_pin_names(tmp_path):
    """RATCHET pointing the other way. If the WRITER renames its keys, this pin must fail rather
    than let the reader drift again -- the failure above is a disagreement, and a disagreement needs
    a guard on both sides or it just moves."""
    from scripts.runner_token_journal import TokenJournal
    tj = TokenJournal("probe-writer", journal_dir=str(tmp_path))
    tj.add_turn(prompt=11, completion=7, model="m")
    files = list(Path(tmp_path).glob("runner_probe-writer_*.json"))
    if not files:
        pytest.skip("the writer did not produce a dated journal in this harness")
    body = json.loads(files[0].read_text(encoding="utf-8"))
    for k in WRITER_KEYS:
        assert k in body, (
            "the writer no longer serializes %r (keys: %r). The reader is pinned to these names; "
            "if they move, move both." % (k, sorted(body)))


def test_gauge_snapshot_still_returns_its_stable_shape():
    """RATCHET. gauge_snapshot promises a shape-stable, exception-free dict; the fix must not make
    it raise on a seat that has never run."""
    from core.comm import engine_vitals as ev
    snap = ev.gauge_snapshot("no-such-agent-at-all")
    assert isinstance(snap, dict) and "tokens" in snap, snap
