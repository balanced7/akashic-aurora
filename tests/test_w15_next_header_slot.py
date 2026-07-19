"""W15 pin: `task list`'s NEXT header and `task next`'s slot gate speak ONE policy.

conductor.next_task returns None while ANY task is ACTIVE (Phase 1 one-at-a-time gate);
format_state's NEXT header used to say "claimable now" over an occupied slot, so the two
surfaces contradicted each other (deepseek W15, verified by kimi walk2 F-b: `task next`
said "none" while `task list` showed 14 claimable). The header now derives from the same
predicate both read (state_view's in_progress). Run: py -m pytest tests/test_w15_next_header_slot.py -q
"""
import os

from core.coord import task_ledger as TL
from core.coord.conductor import next_task


def _ledger(tmp_path):
    # client=None -> git-only, no Redis mirror (hermetic, matches test_task_ledger.py)
    return TL.TaskLedger(os.path.join(str(tmp_path), "tasks.json"), client=None)


def test_header_confesses_occupied_slot(tmp_path):
    L = _ledger(tmp_path)
    a = L.propose("held work", at="t0")
    TL.approve(L, a["id"], at="t1")
    TL.claim(L, a["id"], "claude", at="t2")   # ACTIVE (CLAIMED) occupies the slot
    b = L.propose("queued work", at="t3")
    TL.approve(L, b["id"], at="t4")           # dep-free APPROVED -> lands in v["next"]

    assert next_task(client=None, path=L.path) is None   # the gate refuses...
    text = TL.format_state(path=L.path, client=None)
    assert "claimable now" not in text                   # ...so the header may not promise
    assert "slot occupied by 1 active" in text
    assert b["id"] in text                               # queued work is still listed


def test_header_promises_when_slot_free(tmp_path):
    L = _ledger(tmp_path)
    b = L.propose("ready work", at="t0")
    TL.approve(L, b["id"], at="t1")

    got = next_task(client=None, path=L.path)
    assert got and got["id"] == b["id"]                  # the gate offers...
    text = TL.format_state(path=L.path, client=None)
    assert "NEXT (claimable now):" in text               # ...and the header agrees
