"""S0-gamma-a pins -- wake-detection dedup (scripts/bifrost_wake.py).

Spec: note s0-gamma-wake-dedup (2026-07-21) under the recovery arc's S0 floor
(docs/library/design/20260701_recovery-arc-reconciled-design-superviso_ce9a9e.md). Trigger: ~6 watcher wake-cycles burned in one
hour on LOGICAL duplicates -- dual-write twins (T039a/T044) and RB-26 redeliveries of
mail the session had been woken for but not yet consumed. Cure: a session-scoped
sidecar of already-detected logical ids ((frm, ts, kind), BifrostAPI._dedup_key's
fields); the detect step skips them.

Laws pinned here, RED-first:
  P1  a logical twin is filtered from a wake batch; fresh mail in the same batch still wakes
  P2  an all-twin stretch does NOT wake the seat (the actual burn being cured)
  P3  the sidecar is SESSION-scoped -- another session still wakes on the same mail (fan-out law)
  P4  fail-open -- a corrupt sidecar costs an extra wake, never a missed one
  P5  the sidecar is bounded (SEEN_CAP, newest kept)
  P6  detect-only stays true -- the watcher touches no consume/advance surface
  P7  a tombstoned session's stand-down removes its sidecar (no orphan grows in tempdir)
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import bifrost_wake as bw


class Msg:
    def __init__(self, frm="deepseek", ts="2026-07-21T05:00:00+00:00", kind="handoff",
                 content="hello", meta=None, to="tclaude"):
        self.frm, self.ts, self.kind = frm, ts, kind
        self.content, self.meta, self.to = content, meta or {}, to


class FakeApi:
    """Exposes ONLY the detect-side surface (P6): online_now / online / wake_block.
    Any consume/advance call would AttributeError -- the pin's tripwire."""
    online_now = True

    def __init__(self, batches):
        self.batches = list(batches)
        self.wake_calls = 0

    def online(self):
        return None

    def wake_block(self, timeout_ms=0):
        self.wake_calls += 1
        if self.batches:
            return self.batches.pop(0)
        time.sleep(0.05)          # exhausted -> quiet bus; keep the loop honest, not hot
        return []


def _seat(tmp_path, pid):
    hb = str(tmp_path / "seat.pid")
    with open(hb, "w") as f:
        f.write(str(pid))
    return hb


def _run(api, seen_file, tmp_path, deadline=30, session="sess" + uuid.uuid4().hex[:8]):
    agent = "tclaude"
    hb = _seat(tmp_path, os.getpid())
    rc = bw.watch(agent, deadline, 100, api=api, hb_path=hb, my_pid=os.getpid(),
                  session_id=session, seen_file=seen_file)
    # tempdir hygiene: a cycled exit writes a real re-arm trigger for this throwaway seat
    try:
        os.remove(bw.rearm_trigger_path(agent, session))
    except OSError:
        pass
    return rc


def test_p1_twin_filtered_fresh_still_wakes(tmp_path, capsys):
    seen = str(tmp_path / "wake.seen")
    a = Msg(ts="T1", content="A")
    # wake 1: A delivers and is remembered
    assert _run(FakeApi([[a]]), seen, tmp_path, session="sessP1aaaaa") == 0
    out1 = capsys.readouterr().out
    assert "BIFROST WAKE" in out1 and '"A"' in out1
    # wake 2, same session: A's dual-write twin rides with fresh B -> only B delivers
    twin = Msg(ts="T1", content="A-legacy-copy")          # same (frm, ts, kind) = same logical id
    b = Msg(ts="T2", content="B")
    assert _run(FakeApi([[twin, b]]), seen, tmp_path, session="sessP1aaaaa") == 0
    out2 = capsys.readouterr().out
    assert '"B"' in out2 and "A-legacy-copy" not in out2


def test_p2_all_twins_do_not_wake(tmp_path, capsys):
    seen = str(tmp_path / "wake.seen")
    a = Msg(ts="T1", content="A")
    assert _run(FakeApi([[a]]), seen, tmp_path, session="sessP2aaaaa") == 0
    capsys.readouterr()
    # the burn scenario: every arriving copy is a twin -> the seat must NOT wake
    twins = FakeApi([[Msg(ts="T1", content="A-copy")] for _ in range(3)])
    assert _run(twins, seen, tmp_path, deadline=2, session="sessP2aaaaa") == 0
    out = capsys.readouterr().out
    assert "BIFROST WAKE -- messages" not in out
    assert "twin" in out                       # provenance names the dedup, not silence
    assert twins.wake_calls >= 1


def test_p3_session_scoped_fanout_preserved(tmp_path, capsys):
    assert bw.seen_path("x", "s1") != bw.seen_path("x", "s2")
    assert bw.seen_path("x", "s1") != bw.seen_path("y", "s1")
    seen_a = str(tmp_path / "a.seen")
    seen_b = str(tmp_path / "b.seen")
    a = Msg(ts="T1", content="A")
    assert _run(FakeApi([[a]]), seen_a, tmp_path, session="sessP3aaaaa") == 0
    capsys.readouterr()
    # a DIFFERENT session's watcher sees the same logical packet -> it still wakes
    assert _run(FakeApi([[Msg(ts="T1", content="A")]]), seen_b, tmp_path,
                session="sessP3bbbbb") == 0
    assert "BIFROST WAKE" in capsys.readouterr().out


def test_p4_fail_open_corrupt_sidecar(tmp_path, capsys):
    seen = str(tmp_path / "wake.seen")
    with open(seen, "wb") as f:
        f.write(b"\x00 not json at all {{{")
    assert _run(FakeApi([[Msg(ts="T9", content="fresh")]]), seen, tmp_path,
                session="sessP4aaaaa") == 0
    assert "BIFROST WAKE" in capsys.readouterr().out    # corrupt file never blocks a wake


def test_p5_sidecar_bounded_newest_kept(tmp_path):
    seen = str(tmp_path / "wake.seen")
    keys = [f"frm|ts{i}|kind" for i in range(bw.SEEN_CAP + 500)]
    bw.save_seen(seen, keys)
    stored = json.load(open(seen, encoding="utf-8"))
    assert len(stored) == bw.SEEN_CAP
    assert stored[-1] == keys[-1] and keys[0] not in stored


def test_p6_detect_only_surface(tmp_path):
    # FakeApi defines nothing but the detect surface; P1/P2 passing through watch()
    # without AttributeError IS the pin. Assert the surface was exercised at all.
    seen = str(tmp_path / "wake.seen")
    api = FakeApi([[Msg(ts="T1", content="A")]])
    assert _run(api, seen, tmp_path, session="sessP6aaaaa") == 0
    assert api.wake_calls >= 1
    # and the sidecar holds the canonical logical id -- BifrostAPI._dedup_key's fields
    assert json.load(open(seen, encoding="utf-8")) == ["deepseek|T1|handoff"]


def test_p7_tombstone_standdown_removes_sidecar(tmp_path, monkeypatch, capsys):
    import core.comm.wake_seat as ws
    monkeypatch.setattr(ws, "is_tombstoned", lambda s: True)
    seen = str(tmp_path / "wake.seen")
    bw.save_seen(seen, ["deepseek|T1|handoff"])
    assert _run(FakeApi([]), seen, tmp_path, session="sessP7aaaaa") == 0
    assert "tombstoned" in capsys.readouterr().out
    assert not os.path.exists(seen)            # a dead-by-record session leaves no orphan
