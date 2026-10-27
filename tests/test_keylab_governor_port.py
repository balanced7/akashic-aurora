"""The burst ceiling counted per PORT, across processes (governor.PortGovernor).

Before 2026-10-27 each winmidi.MidiOut built its own BurstGovernor, so the screen service, the VJ engine, every CLI
call and every probe each had 12 packets per 100 ms, and their sum on the DAW port had no ceiling (section "Start
here", point 3, of research/reviewed/keylab-liberation-2026-10-22/keylab-dev-guidance-and-hang-guide-2026-10-27.md).
The headline test runs three real processes against one port, one of them with busy Python threads, and checks when
the merged sends reached the driver (not only the slots: a late-running sender once put 13 on the driver while the
slots held 12). No keyboard: each process sends to keylab_fake_winmm.FakeWinMM, and every bucket lives in a
temporary directory.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import keylab_fake_winmm as F
from arsenal.keylab import governor as G
from arsenal.keylab import winmidi as W
from arsenal.keylab.governor import SAFE_BURST, WINDOW_S, max_in_window

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
DAW = "KeyLab 88 mk3 DAW"
LED = bytes([0xF0, 0x00, 0x20, 0x6B, 0x7F, 0x42, 0x00, 0x02, 0x03, 0x52, 0x7F, 0x00, 0x00, 0x00, 0xF7])


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += max(s, 1e-6)


@pytest.fixture(autouse=True)
def _private_governor_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(G.GOVERNOR_DIR_ENV, str(tmp_path / "governor"))


@pytest.fixture
def fake(monkeypatch):
    f = F.FakeWinMM()
    monkeypatch.setattr(W, "_winmm", lambda: f)
    return f


# --- the headline: processes ---------------------------------------------------------------------------------------

CHILD = r'''
import json, sys, threading, time
repo, tests, start_at, n, out_path, busy = (sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]),
                                            sys.argv[5], int(sys.argv[6]))
sys.path[:0] = [repo, tests]
import keylab_fake_winmm as F
from arsenal.keylab import winmidi as W
fake = F.FakeWinMM()
W._winmm = lambda: fake
out = W.MidiOut(prefer="daw")                 # exactly as the screen service, the VJ engine and the CLI open it
out.governor.record = True
stop = False


def spin():                                   # pure Python that holds the GIL, like the VJ engine's analysis threads
    x = 0
    while not stop:
        x += 1


spinners = [threading.Thread(target=spin, daemon=True) for _ in range(busy)]
for s in spinners:
    s.start()
ready = time.perf_counter()
while time.perf_counter() < start_at:
    time.sleep(0.001)
for i in range(n):                            # an unpaced flood
    out.send_sysex(bytes([0xF0, 0x00, 0x20, 0x6B, 0x7F, 0x42, 0x00, 0x02, 0x03, 0x52, i & 0x7F, 0, 0, 0, 0xF7]))
stop = True
out.close()
with open(out_path, "w") as f:                # "driver": when each midiOutLongMsg reached the (fake) driver
    json.dump({"admits": list(out.governor.log), "driver": [t for t, _b in fake.long_msgs], "ready": ready}, f)
'''


def test_three_processes_on_one_port_never_exceed_the_ceiling_together_at_the_driver(tmp_path):
    # One sender's Python is busy (two spinning threads): its sends reach the driver well after their slots. Before
    # 2026-10-27 round 2 the slots held 12 per 100 ms while the driver saw 13 (scratchpad adversarial run, 6 of 6).
    n, k, busy = 36, 3, (2, 0, 0)
    script = tmp_path / "child.py"
    script.write_text(CHILD, encoding="utf-8")
    env = dict(os.environ, **{G.GOVERNOR_DIR_ENV: str(tmp_path / "shared-governor")})
    start_at = time.perf_counter() + 3.0      # perf_counter is QueryPerformanceCounter: one clock for the machine
    procs = [subprocess.Popen([sys.executable, str(script), str(ROOT), str(TESTS), repr(start_at), str(n),
                               str(tmp_path / f"child{i}.json"), str(busy[i])], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(k)]
    for p in procs:
        _out, err = p.communicate(timeout=180)
        assert p.returncode == 0, err
    runs = [json.loads((tmp_path / f"child{i}.json").read_text()) for i in range(k)]
    assert all(r["ready"] < start_at for r in runs), "a child was late to the start line: the floods did not overlap"
    assert all(len(r["driver"]) == n for r in runs)
    spans = [(min(r["driver"]), max(r["driver"])) for r in runs]
    assert max(s[0] for s in spans) < min(s[1] for s in spans), "the three floods ran at the same time"
    driver = [t for r in runs for t in r["driver"]]
    assert max_in_window(driver, WINDOW_S) <= SAFE_BURST, "what reaches the driver holds the port's ceiling"
    slots = [t for r in runs for t in r["admits"]]
    assert len(slots) == n * k and max_in_window(slots, WINDOW_S) == SAFE_BURST, "the port still got its budget"


# --- one process, two outputs on the same port ---------------------------------------------------------------------

def test_midiout_governs_by_the_port_it_opened(fake):
    out = W.MidiOut(prefer="daw")
    assert isinstance(out.governor, G.PortGovernor) and out.governor.port == DAW and out.governor.shared
    assert Path(out.governor.path).parent == Path(os.environ[G.GOVERNOR_DIR_ENV])
    out.close()
    assert W.MidiOut(prefer="daw", governor=False).governor is None, "a limit probe can still switch it off"


def test_two_outputs_in_one_process_share_the_ceiling(fake):
    outs = [W.MidiOut(prefer="daw"), W.MidiOut(prefer="daw")]
    for o in outs:
        o.governor.record = True

    def flood(o):
        for _ in range(30):
            o.send_sysex(LED)

    threads = [threading.Thread(target=flood, args=(o,)) for o in outs]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    merged = outs[0].governor.log + outs[1].governor.log
    assert len(merged) == 60
    assert max_in_window(merged, WINDOW_S) <= SAFE_BURST
    for o in outs:
        o.close()


# --- the bucket itself, on a fake clock ----------------------------------------------------------------------------

def _gov(tmp_path, clk, port=DAW, **kw):
    g = G.PortGovernor(port, state_dir=tmp_path / "b", clock=clk.now, sleep=clk.sleep, **kw)
    g.record = True
    return g


def test_two_governors_on_one_bucket_never_exceed_the_ceiling(tmp_path):
    clk = FakeClock()
    a, b = _gov(tmp_path, clk), _gov(tmp_path, clk)
    for i in range(90):
        (a if i % 3 else b).admit()
        clk.t += 0.0004
    merged = a.log + b.log
    assert len(merged) == 90 and max_in_window(merged, WINDOW_S) <= SAFE_BURST
    assert a.waited_s + b.waited_s > 0


def test_sends_that_lag_their_slots_are_still_held_to_the_ceiling_at_the_driver(tmp_path):
    clk = FakeClock()
    a, b = _gov(tmp_path, clk), _gov(tmp_path, clk)
    driver = []

    def send():
        driver.append(clk.now())

    t0 = clk.t
    for _ in range(SAFE_BURST):
        a.admit()                                # twelve slots at t0
    clk.t = t0 + 0.09                            # a's Python was busy: its twelve sends reach the driver 90 ms late
    for _ in range(SAFE_BURST):
        a.gate(send)
    b.admit()                                    # b's slot is fine by the slots: one window after a's
    b.gate(send)
    assert max_in_window(a.log + b.log, WINDOW_S) <= SAFE_BURST
    assert max_in_window(driver, WINDOW_S) <= SAFE_BURST, "the driver never sees a thirteenth"
    assert driver[-1] >= t0 + 0.09 + WINDOW_S - 1e-9 and b.gate_waited_s > 0


def test_a_send_still_in_flight_counts_against_every_other_sender(tmp_path):
    clk = FakeClock()
    a, b = _gov(tmp_path, clk), _gov(tmp_path, clk)
    driver = []

    def send():
        driver.append(clk.now())

    for _ in range(SAFE_BURST - 1):
        a.gate(send)

    def slow_send():                             # a's twelfth is inside the driver call when b wants to send
        send()
        b.gate(send)

    a.gate(slow_send)
    assert len(driver) == SAFE_BURST + 1
    assert max_in_window(driver, WINDOW_S) <= SAFE_BURST


def test_a_send_left_in_flight_by_a_dead_process_stops_counting_after_a_while(tmp_path):
    clk = FakeClock()
    dead = _gov(tmp_path, clk)
    for _ in range(SAFE_BURST):
        dead._gate_enter()                       # registered, then the process died inside the driver call
    g = _gov(tmp_path, clk)
    t0 = clk.t
    g.gate(lambda: None)
    assert clk.t - t0 >= G.FLIGHT_STALE_S, "held while they might still be sending"
    assert clk.t - t0 < G.FLIGHT_STALE_S + 0.1, "then let go"


def test_a_busy_process_holds_the_port_lock_for_microseconds(tmp_path, monkeypatch):
    # Every send takes the port's cross-process lock. A thread that gives up the GIL while it holds that lock (a
    # read() or write() on the bucket file did) waits behind the process's busy threads, and every other process
    # waits with it: 63 ms per admit (median, 2 spinning threads) before round 2 (scratchpad hold_probe.py).
    holds, t = [], [0.0]
    lock, unlock = G._lock_fd, G._unlock_fd

    def timed_lock(fd):
        lock(fd)
        t[0] = time.perf_counter()

    def timed_unlock(fd):
        holds.append(time.perf_counter() - t[0])
        unlock(fd)

    monkeypatch.setattr(G, "_lock_fd", timed_lock)
    monkeypatch.setattr(G, "_unlock_fd", timed_unlock)
    stop = threading.Event()

    def spin():
        x = 0
        while not stop.is_set():
            x += 1

    spinners = [threading.Thread(target=spin, daemon=True) for _ in range(2)]
    for s in spinners:
        s.start()
    g = G.PortGovernor(DAW, state_dir=tmp_path / "b")
    try:
        for _ in range(SAFE_BURST):
            g.admit()
            g.gate(lambda: time.sleep(0))        # the real driver call gives up the GIL too
    finally:
        stop.set()
        for s in spinners:
            s.join(timeout=5)
        g.close()
    holds.sort()
    assert len(holds) >= 3 * SAFE_BURST
    assert holds[len(holds) // 2] < 0.005, f"median lock hold {holds[len(holds) // 2] * 1e3:.1f} ms"


def test_a_renamed_port_is_the_same_bucket_and_another_port_is_not(tmp_path):
    assert G.port_key("2- KeyLab 88 mk3 DAW") == G.port_key(DAW) == "keylab-88-mk3-daw"
    clk = FakeClock()
    daw = _gov(tmp_path, clk)
    for _ in range(SAFE_BURST):
        daw.admit()
    t = clk.t
    _gov(tmp_path, clk, port="KeyLab 88 mk3 MIDI").admit()
    assert clk.t == t, "the MIDI port has its own budget"
    _gov(tmp_path, clk, port="3- KeyLab 88 mk3 DAW").admit()
    assert clk.t > t, "a renamed DAW port shares the DAW budget"


def test_a_governor_that_exits_still_counts_for_the_next_one(tmp_path):
    clk = FakeClock()
    first = _gov(tmp_path, clk)
    for _ in range(SAFE_BURST):
        first.admit()
    first.close()                                 # a CLI call that sent 12 packets and exited
    second = _gov(tmp_path, clk)
    second.admit()
    assert max_in_window(first.log + second.log, WINDOW_S) <= SAFE_BURST


def _overwrite(path, data: bytes) -> None:
    """Write over the bucket in place, as another process would (it is memory-mapped, so it cannot be truncated)."""
    with open(path, "r+b") as f:
        f.write(data.ljust(G._STATE_BYTES))


def test_a_corrupt_bucket_costs_one_window_and_heals(tmp_path):
    clk = FakeClock()
    g = _gov(tmp_path, clk)
    _overwrite(g.path, b"\x00garbage{")
    t0 = clk.t
    g.admit()
    assert clk.t - t0 >= WINDOW_S, "unreadable state: assume the window is full"
    for _ in range(SAFE_BURST - 1):
        g.admit()
    g.gate(lambda: None)
    assert json.loads(Path(g.path).read_text())["times"], "the bucket was rewritten"
    _overwrite(g.path, b"{not json")
    t1 = clk.t
    g.gate(lambda: None)
    assert clk.t - t1 >= WINDOW_S, "the gate assumes a full window too"


def test_times_from_another_boot_are_ignored(tmp_path):
    clk = FakeClock()
    g = _gov(tmp_path, clk)
    far = clk.t + 5000.0
    _overwrite(g.path, json.dumps({"times": [far] * SAFE_BURST, "ends": [far] * SAFE_BURST,
                                   "flight": [[1, far]] * SAFE_BURST}).encode())
    t0 = clk.t
    g.admit()
    g.gate(lambda: None)
    assert clk.t == t0


def test_a_holder_that_never_lets_go_is_waited_out_not_obeyed_forever(tmp_path):
    clk = FakeClock()
    g = _gov(tmp_path, clk, lock_timeout=0.05)
    fd = os.open(str(g.path), os.O_RDWR | getattr(os, "O_BINARY", 0))
    try:
        G._lock_fd(fd)                            # another process frozen while holding the lock
        t0 = clk.t
        g.admit()
        assert g.fallbacks == 1 and clk.t - t0 >= WINDOW_S
    finally:
        G._unlock_fd(fd)
        os.close(fd)


def test_an_unusable_state_dir_falls_back_to_the_in_process_ceiling(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x")
    clk = FakeClock()
    g = G.PortGovernor(DAW, state_dir=blocker / "sub", clock=clk.now, sleep=clk.sleep)
    g.record = True
    assert not g.shared
    driver = []
    for i in range(40):
        g.admit()
        if i == 3:
            clk.t += 0.05                        # one late send bunches the next ones at the driver
        g.gate(lambda: driver.append(clk.now()))
    assert max_in_window(g.log, WINDOW_S) <= SAFE_BURST
    assert len(driver) == 40 and max_in_window(driver, WINDOW_S) <= SAFE_BURST


def test_a_limit_the_bucket_cannot_hold_is_refused_and_a_full_bucket_stays_bounded(tmp_path):
    with pytest.raises(ValueError):
        G.PortGovernor(DAW, limit=G._LIMIT_MAX + 1, state_dir=tmp_path / "b")
    clk = FakeClock()
    g = _gov(tmp_path, clk, limit=G._LIMIT_MAX, window=10.0)
    for _ in range(G._LIMIT_MAX):
        g.admit()
        g.gate(lambda: None)
        clk.t += 0.001
    raw = Path(g.path).read_bytes()
    state = json.loads(raw)
    assert len(raw) == G._STATE_BYTES and len(state["times"]) == len(state["ends"]) == G._LIMIT_MAX
    clk.t += 20.0                                # the worst case: a full window of slots and of sends in flight
    h = _gov(tmp_path, clk, limit=G._LIMIT_MAX, window=10.0)
    for _ in range(G._LIMIT_MAX):
        h.admit()
        h._gate_enter()
        clk.t += 0.001
    raw = Path(h.path).read_bytes()
    state = json.loads(raw)
    assert len(raw) == G._STATE_BYTES and len(state["times"]) == len(state["flight"]) == G._LIMIT_MAX


def test_the_default_bucket_is_the_main_checkouts_even_from_a_worktree(tmp_path, monkeypatch):
    main = tmp_path / "main"
    (main / ".git" / "worktrees" / "wf_x").mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'wf_x'}\n")
    assert G._main_checkout(wt) == main
    assert G._main_checkout(main) == main
    monkeypatch.delenv(G.GOVERNOR_DIR_ENV)
    assert G.default_state_dir().parts[-4:] == ("state", "arsenal", "keylab", "governor")
