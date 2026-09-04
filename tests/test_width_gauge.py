"""Width-gauge pins — operator ruling art_20260903_width-ruling-2026-09-03_369243 made executable.

ORG Part 3's law, given teeth by Daniil's verbatim "Approve" (2026-09-03 night): the cap is TWO
watches; a third ACTIVE round opens only by naming what stops (`pauses:`) or by the operator's
recorded word (`operator_ruling` — a RECORDED word, never a sender name: gateway attribution is
not speaker identity). The cap refuses only SILENCE about the cost — never the work, never the
operator. Phase 1's one-at-a-time serialize gate is superseded BY RULING; its pin in
test_task_ledger.py retires to the two-watch form in the same slice.
Run: py -m pytest tests/test_width_gauge.py -q
"""
import os

import pytest

from core.coord import task_ledger as TL


def fresh(tmp_path):
    # client=None -> git-only, no Redis mirror (hermetic, same idiom as test_task_ledger)
    return TL.TaskLedger(os.path.join(str(tmp_path), "tasks.json"), client=None)


def _staged(L, name):
    """propose -> approve -> claim with disjoint files, so only the width gate applies."""
    t = L.propose(name, files=[f"{name}.py"], at="t0")
    TL.approve(L, t["id"], at="t1")
    TL.claim(L, t["id"], "claude", at="t2")
    return t


def test_two_watches_open_without_ceremony(tmp_path):
    # RED against Phase 1: the serialize gate refuses the SECOND start; ruling 369243 licenses two.
    L = fresh(tmp_path)
    a, b = _staged(L, "build"), _staged(L, "design")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    open_now = {t["id"] for t in L.in_progress() if t["status"] == TL.IN_PROGRESS}
    assert open_now == {a["id"], b["id"]}


def test_third_watch_without_pauses_refuses_and_teaches(tmp_path):
    L = fresh(tmp_path)
    a, b, c = _staged(L, "build"), _staged(L, "design"), _staged(L, "third")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    with pytest.raises(TL.LedgerError) as e:
        TL.start(L, c["id"], at="t4")
    msg = str(e.value)
    assert "pauses" in msg, "the refusal must name the door, not just refuse"
    assert "369243" in msg, "the refusal must cite the ruling -- law, not vibes"
    assert "two-watch" in msg


def test_third_watch_with_pauses_opens_and_records(tmp_path):
    L = fresh(tmp_path)
    a, b, c = _staged(L, "build"), _staged(L, "design"), _staged(L, "third")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    TL.start(L, c["id"], at="t4", pauses=b["id"])   # the cost is spoken: what stops is named
    row = L.get(c["id"])
    assert row["status"] == TL.IN_PROGRESS
    assert row["pauses"] == b["id"], "pauses is a recorded field on the row, not a mere password"
    assert any(h.get("pauses") == b["id"] for h in row["history"]), \
        "the named pause must survive in history -- announcements are receipts"


def test_operator_recorded_word_never_refused(tmp_path):
    # ORG: "the cap never refuses the operator." The override is his RECORDED word -- never a
    # sender-name check (gateway_attribution_is_not_speaker_identity).
    L = fresh(tmp_path)
    a, b, c = _staged(L, "build"), _staged(L, "design"), _staged(L, "third")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    TL.start(L, c["id"], at="t4", operator_ruling="Daniil: do it anyway, pause nothing")
    row = L.get(c["id"])
    assert row["status"] == TL.IN_PROGRESS
    assert any(h.get("operator_ruling") for h in row["history"]), \
        "the operator's word is recorded in history, same as T352's done-exit"


def test_second_watch_needs_no_pauses_field_and_records_none(tmp_path):
    # The widening must not overshoot: two watches are LAWFUL, no ceremony, no phantom fields.
    L = fresh(tmp_path)
    a, b = _staged(L, "build"), _staged(L, "design")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    assert "pauses" not in L.get(b["id"]), "no pauses field invented where none was declared"
