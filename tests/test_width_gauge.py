"""Width-gauge pins — operator ruling art_20260903_width-ruling-2026-09-03_369243 made executable.

ORG Part 3's law, given teeth by Daniil's verbatim "Approve" (2026-09-03 night): the cap is TWO
watches; a third ACTIVE round opens only by naming what stops (`pauses:`) or by the operator's
recorded word (`operator_ruling` — a RECORDED word, never a sender name: gateway attribution is
not speaker identity). The cap refuses only SILENCE about the cost — never the work, never the
operator. Phase 1's one-at-a-time serialize gate is superseded BY RULING; its pin in
test_task_ledger.py retires to the two-watch form in the same slice.
Run: py -m pytest tests/test_width_gauge.py -q
"""
import json
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


# --- observability half (defer 2955dae7eb): the doctor renders open-watch count against the cap ---
# Ruling 369243 move 3, verbatim: "the doctor renders open-watch count against the cap". The gate
# half landed in 0c22d0ef; until these pins the cap was visible ONLY BY REFUSING -- two watches
# open, and neither boot nor `doctor` said so. The read goes through the T352 AKASHIC_TASKS_PATH
# door (a git-only TaskLedger: no Redis mirror, nothing written). Fail-open by the doctor's own
# law (it must never wedge a boot): an absent ledger is 0/2, a corrupt one is ?/2 plus the why.


def _hermetic_probes():
    """The fleet-doctor's hermetic probe set (mirrors tests/test_fleet_doctor.py::_probes): a
    healthy-idle seat with no live facet read -- the only live thing in the round is the ledger."""
    import time
    now = time.time()
    return dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": now - 5, "beat_ts": now - 1},
        progress=lambda a: None, backlog=lambda a: 0, stalled_since=lambda a, present: None,
        halted=lambda a: None, lane_health=lambda a: None, token_cost=lambda a: None,
        bench_count=lambda a: 0, now=now)


def _isolated_ledger(tmp_path, monkeypatch):
    """A tmp ledger that the doctor's read-only door resolves through AKASHIC_TASKS_PATH."""
    path = os.path.join(str(tmp_path), "tasks.json")
    monkeypatch.setenv("AKASHIC_TASKS_PATH", path)
    return path, TL.TaskLedger(path, client=None)


def test_doctor_renders_open_watches_against_the_cap(tmp_path, monkeypatch):
    # RED at HEAD: examine_fleet's report has no "watches" and its summary never names the cap.
    from core.comm.doctor import examine_fleet
    path, L = _isolated_ledger(tmp_path, monkeypatch)
    a, b = _staged(L, "build"), _staged(L, "design")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    rep = examine_fleet(["claude"], probes=_hermetic_probes())
    w = rep["watches"]
    assert (w["open"], w["cap"], w["ids"], w["over"], w["error"]) == \
        (2, 2, [a["id"], b["id"]], False, None)
    assert "watches 2/2" in rep["summary"], "the count rides the one line boot and doctor both print"
    assert a["id"] in rep["summary"] and b["id"] in rep["summary"], "ids, so the reader knows WHICH"
    assert rep["findings"] == [], "at cap is lawful: the line informs, it does not alarm"


def test_doctor_fails_open_on_an_unreadable_ledger(tmp_path, monkeypatch):
    from core.comm.doctor import examine_fleet
    path = os.path.join(str(tmp_path), "tasks.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not json")
    monkeypatch.setenv("AKASHIC_TASKS_PATH", path)
    rep = examine_fleet(["claude"], probes=_hermetic_probes())     # must not raise
    w = rep["watches"]
    assert w["open"] is None and w["error"], "a corrupt ledger is REPORTED, never raised through a boot"
    assert "watches ?/2" in rep["summary"] and "ledger" in rep["summary"]


def test_cap_is_one_named_constant_shared_by_gate_and_doctor(tmp_path, monkeypatch):
    assert TL.WATCH_CAP == 2, "ruling 369243: two watches -- one build, one design/research"
    # a fresh clone (no state/coord/tasks.json) renders 0/2 -- an absence is not an error
    w = TL.open_watches(os.path.join(str(tmp_path), "absent.json"))
    assert (w["open"], w["cap"], w["ids"], w["over"], w["error"]) == (0, 2, [], False, None)
    # the gate CONSULTS the constant (no second literal): widen it and a third watch opens in silence
    monkeypatch.setattr(TL, "WATCH_CAP", 3)
    L = fresh(tmp_path)
    a, b, c = _staged(L, "build"), _staged(L, "design"), _staged(L, "third")
    for t in (a, b, c):
        TL.start(L, t["id"], at="t3")
    w = TL.open_watches(L.path)
    assert (w["open"], w["cap"], w["over"]) == (3, 3, False)


def test_silent_width_around_the_gate_is_a_dashboard_finding(tmp_path, monkeypatch):
    # The gate refuses a third watch that names no cost; a ledger widened AROUND it (a hand edit,
    # an older writer) must not render as normal -- an absence that reads as normal is the house's
    # oldest failure class. Licensed width (pauses= recorded) is the ruling working: no finding.
    from core.comm.doctor import examine_fleet
    path, L = _isolated_ledger(tmp_path, monkeypatch)
    a, b, c = _staged(L, "build"), _staged(L, "design"), _staged(L, "third")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")
    TL.start(L, c["id"], at="t4", pauses=b["id"])            # lawful: the cost is spoken
    rep = examine_fleet(["claude"], probes=_hermetic_probes())
    assert rep["watches"]["over"] is True and rep["watches"]["silent"] == [a["id"], b["id"]]
    assert "watches 3/2" in rep["summary"]
    assert not [f for f in rep["findings"] if f["state"] == "watch_cap_silent"], \
        "a third watch with its cost recorded is the ruling working, not a finding"
    # now strip the recorded cost, as an edit around the gate would
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for t in data["tasks"]:
        t.pop("pauses", None)
        for h in t["history"]:
            h.pop("pauses", None)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    rep = examine_fleet(["claude"], probes=_hermetic_probes())
    assert rep["watches"]["silent"] == [a["id"], b["id"], c["id"]]
    found = [f for f in rep["findings"] if f["state"] == "watch_cap_silent"]
    assert len(found) == 1 and found[0]["grade"] == "dashboard"
    assert "369243" in found[0]["line"] and c["id"] in found[0]["line"] and found[0]["drill"]
