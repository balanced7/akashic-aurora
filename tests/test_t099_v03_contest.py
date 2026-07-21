"""T099 contest -- the chorus door for toast (kimi R2 build). 6 pins, pre-registered.

P1  receipt verified -> tier VERIFIED, both surfaces land
P2  receipt bad + no force -> REFUSED, nothing sent
P3  receipt bad + force -> GUESS confessed in line AND note
P4  existing toast note -> contest APPENDS (prior body preserved, verse accrues)
P5  no prior toast -> contest opens the thread alone (confessed)
P6  self-contest / empty credit / over-long credit -> refused before any write
"""
import core.toolbelt.contest as contest


class FakeStore:
    def __init__(self, hits):
        self._hits = hits          # {experiment_id: agent_id}
    def _load_experiment(self, exp_id):
        aid = self._hits.get(exp_id)
        return {"agent_id": aid} if aid else {}
    def load_all_learnings_from_store(self):
        return [{"experiment_name": k, "agent_id": v} for k, v in self._hits.items()]


def _rig(prior=None, store=None):
    sent, notes = [], {}
    if prior:
        notes["toast:deepseek-toast-beta2-freeplay-2026-07-21"] = prior
    rig = {
        "bus_send": lambda to, kind, text: sent.append((to, kind, text)),
        "note_read": lambda t: notes.get(t),
        "note_write": lambda t, b: notes.__setitem__(t, b),
        "store": store or FakeStore({"toast_beta2_freeplay_2026-07-21": "deepseek"}),
        "_sent": sent, "_notes": notes,
    }
    return rig


def test_p1_verified_contest_lands_both_surfaces():
    r = _rig()
    res = contest.send("kimi", "deepseek", "toast_beta2_freeplay_2026-07-21",
                       "saved me re-searching the receipt seam", **{k: v for k, v in r.items() if not k.startswith("_")})
    assert res["tier"] == "VERIFIED", res
    assert res["bus"] == "sent"
    assert ("appended" in res["note"]) or ("opened" in res["note"]), res["note"]
    assert r["_sent"] and "CONTESTED VERIFIED" in r["_sent"][0][2]


def test_p2_bad_receipt_refuses_silently_nothing_sent():
    r = _rig(store=FakeStore({}))
    try:
        contest.send("kimi", "deepseek", "no_such_exp", "credit", **{k: v for k, v in r.items() if not k.startswith("_")})
        assert False, "should have refused"
    except ValueError as e:
        assert "REFUSED" in str(e)
    assert r["_sent"] == [] and r["_notes"] == {}, "refusal must not write anywhere"


def test_p3_forced_contest_confesses_guess_both_artifacts():
    r = _rig(store=FakeStore({}))
    res = contest.send("kimi", "deepseek", "no_such_exp", "I believe it anyway",
                       force=True, **{k: v for k, v in r.items() if not k.startswith("_")})
    assert res["tier"] == "GUESS"
    assert "GUESS" in r["_sent"][0][2] and "unverified" in r["_sent"][0][2]
    body = list(r["_notes"].values())[0]
    assert "GUESS" in body


def test_p4_contest_appends_prior_body_preserved():
    prior = "TOAST (VERIFIED) -- 2026-07-21 03:37\nfrom: claude   to: deepseek\nreceipt: toast_beta2_freeplay_2026-07-21\ncredit: the seam\nverification: VERIFIED (exact)"
    r = _rig(prior=prior)
    contest.send("kimi", "deepseek", "toast_beta2_freeplay_2026-07-21",
                 "same seam saved my fence pass", **{k: v for k, v in r.items() if not k.startswith("_")})
    body = list(r["_notes"].values())[0]
    assert prior in body, "the original toast must survive verbatim"
    assert "contested (VERIFIED)" in body and "by: kimi" in body


def test_p5_no_prior_toast_opens_thread_confessed():
    r = _rig()
    res = contest.send("kimi", "deepseek", "toast_beta2_freeplay_2026-07-21",
                       "credit where none was recorded", **{k: v for k, v in r.items() if not k.startswith("_")})
    assert "opened" in res["note"], res


def test_p6_guards_fire_before_any_write():
    r = _rig()
    for bad in [("kimi", "kimi", "x", "self-contest"), ("kimi", "deepseek", "x", ""),
                ("kimi", "deepseek", "x", "y" * 300)]:
        try:
            contest.send(bad[0], bad[1], "toast_beta2_freeplay_2026-07-21", bad[3],
                         **{k: v for k, v in r.items() if not k.startswith("_")})
            assert False, f"should refuse: {bad[3][:20]}"
        except ValueError:
            pass
    assert r["_sent"] == [] and r["_notes"] == {}
