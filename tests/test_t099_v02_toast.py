"""
toast (T099 · tools-hunt BETA-2) -- pre-registered RED before core/toolbelt/toast.py exists.

Laws under test (kimi's B3, founding leaderboard #8):
  1. A receipt naming a REAL lesson of the toasted agent sends VERIFIED, on BOTH surfaces
     (live bus line + durable note), and the note title is stable (re-toast supersedes,
     never piles up).
  2. A receipt that does not verify REFUSES loudly -- no bus, no note -- and names why.
  3. force=True sends it anyway, honestly labeled GUESS, in BOTH artifacts.
  4. A lesson owned by a DIFFERENT seat never verifies for this toast (no mis-credit).
  5. Injected senders make the whole thing testable offline (the resolve_and_run seam).
Run: py -m pytest tests/test_t099_v02_toast.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeStore:
    """The learning-store contract, in memory: _load_experiment + load_all_learnings_from_store."""
    def __init__(self, records):
        self._records = records   # list of dicts with experiment_name + agent_id

    def _load_experiment(self, exp_id):
        for r in self._records:
            if r.get("experiment_name") == exp_id:
                return r
        return None

    def load_all_learnings_from_store(self):
        return list(self._records)


def _recorders():
    sent, notes = [], {}
    return sent, notes, (lambda to, kind, text: sent.append((to, kind, text))), \
           (lambda title, body: notes.__setitem__(title, body))


def test_verified_receipt_sends_both_surfaces():
    from core.toolbelt import toast
    store = FakeStore([{"experiment_name": "wake_watcher_insta_fires_lane_divergence",
                        "agent_id": "claude"}])
    sent, notes, bus, note = _recorders()
    res = toast.send("kimi", "claude", "wake_watcher_insta_fires_lane_divergence",
                     "your lane-divergence lesson saved me ~6 hops tonight",
                     bus_send=bus, note_write=note, store=store)
    assert res["tier"] == "VERIFIED"
    assert res["bus"] == "sent" and res["note"] == "written"
    assert sent and sent[0][0] == "claude" and "[VERIFIED]" in sent[0][2]
    assert "receipt: wake_watcher_insta_fires_lane_divergence" in sent[0][2]
    assert list(notes) == [res["note_title"]]
    assert notes[res["note_title"]].startswith("TOAST (VERIFIED)")


def test_unverified_receipt_refuses_loudly_no_surfaces():
    from core.toolbelt import toast
    store = FakeStore([])
    sent, notes, bus, note = _recorders()
    try:
        toast.send("kimi", "deepseek", "no-such-lesson", "saved me hops",
                   bus_send=bus, note_write=note, store=store)
        assert False, "a bad receipt must refuse"
    except ValueError as e:
        assert "REFUSED" in str(e) and "no experiment matching" in str(e)
    assert not sent and not notes, "refusal touches neither surface"


def test_forced_unverified_sends_honestly_labeled_guess():
    from core.toolbelt import toast
    store = FakeStore([])
    sent, notes, bus, note = _recorders()
    res = toast.send("kimi", "deepseek", "half-remembered-lesson", "I think this saved me",
                     force=True, bus_send=bus, note_write=note, store=store)
    assert res["tier"] == "GUESS"
    assert "[GUESS" in sent[0][2] and "unverified" in sent[0][2]
    assert "TOAST (GUESS)" in notes[res["note_title"]]


def test_receipt_owned_by_other_seat_never_verifies():
    from core.toolbelt import toast
    store = FakeStore([{"experiment_name": "wake_watcher_insta_fires_lane_divergence",
                        "agent_id": "claude"}])
    sent, notes, bus, note = _recorders()
    try:
        toast.send("kimi", "deepseek", "wake_watcher_insta_fires_lane_divergence",
                   "saved me hops", bus_send=bus, note_write=note, store=store)
        assert False, "crediting the wrong seat must refuse"
    except ValueError as e:
        assert "belongs to claude, not deepseek" in str(e)
    assert not sent and not notes


def test_note_title_is_stable_for_retoast_supersession():
    from core.toolbelt import toast
    t1 = toast.note_title("claude", "wake_watcher_insta_fires_lane_divergence")
    t2 = toast.note_title("claude", "wake_watcher_insta_fires_lane_divergence")
    assert t1 == t2 and t1.startswith("toast:")
    assert toast.note_title("deepseek", "wake_watcher_insta_fires_lane_divergence") != t1


def test_empty_credit_and_oversize_credit_refuse():
    from core.toolbelt import toast
    store = FakeStore([{"experiment_name": "x", "agent_id": "claude"}])
    sent, notes, bus, note = _recorders()
    for bad in ("", "   ", "z" * 401):
        try:
            toast.send("kimi", "claude", "x", bad, bus_send=bus, note_write=note, store=store)
            assert False, f"credit {bad[:10]!r} must refuse"
        except ValueError:
            pass
    assert not sent and not notes
