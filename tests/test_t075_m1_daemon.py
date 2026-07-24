"""T075 M1-ALPHA PRE-REGISTERED ACCEPTANCE -- the daemon skeleton's governing pins.

Spec: docs/library/report/20260715_t060-m1-continuous-presence-reconciliati_32cac4.md (slice M1-alpha:
lock + presence + heartbeat + bus-loss guard + stable token + clean SIGINT;
NO consume-path moves, NO child runtimes). deepseek's blind-half pin table governs
(deepseek-t060-m1-design-2026-07-15.md sec.4): M1-P1, M1-P2, M1-P11, M1-P12.
claude builds, deepseek verifies -- this file is committed RED before the build.

DRILL-SCALE DISCLOSURE (timescale.py discipline): the pins' production durations
(P1 "survives 60s", P2 "ts within last 10s") run here under
AKASHIC_TIMEOUT_MULTIPLIER shrink -- the SEMANTIC is pinned, the wall-clock is
scaled exactly the way the T030/T073 drills scale. Mapping stated per test.

BUILD REFINEMENTS (flagged for deepseek's verify, T073 precedent):
  R-a1  SAME-TOKEN TWIN REFUSAL: the stable dotfile token (M1-P12) makes a
        double-launch on one host present as the LOCK'S OWN token with a foreign
        pid -- runner_lock's re-entrant path would welcome it. The daemon
        pre-checks holder(): same token + different pid = live twin = REFUSE
        (exit 0, teaching text). No pid liveness probe (os.kill(pid,0) on
        Windows TERMINATES the target -- TTL truth resolves crashed
        predecessors within one lock TTL instead).
  R-a2  ALPHA INVARIANT woven into every drill: the daemon NEVER creates its
        agent's cursor key (the consume path does not move in wave 1 --
        reconciliation ruling 1).

STDOUT CONTRACT (operator-facing provenance, wake-listener discipline; these
lines ARE the interface the pins parse):
  [daemon] up agent=<a> ns=<ns> token=<tok> gen=<n> ttl=<s>s hb=<s>s pid=<pid>
  [daemon] refused agent=<a>: held by pid=<p> token8=<t8> (M1-P11 coexistence -- no steal)
  [daemon] refused agent=<a>: live twin pid=<p> holds MY token (delete ~/.akashic/daemon_<a>.id to fork identity)
  [daemon] stand-down agent=<a>: lock lost -- exiting 0
  [daemon] clean exit agent=<a> reason=<sigint|max-runtime> (lock released)
Exit codes: 0 = every benign ending (up->clean, refusal, stand-down);
2 = bus offline at launch (host supervisor backoff owns retries); 1 = fault.

Run: py -m pytest tests/test_t075_m1_daemon.py -q   (live Redis required)
"""
import json
import os
import re
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DAEMON = os.path.join(ROOT, "scripts", "bifrost_daemon.py")


def _control_client():
    """A raw Redis handle for key asserts -- ns-agnostic (keys are composed
    manually per drill namespace). None when the live bus is unreachable."""
    try:
        from core.comm.bus import Bus
        b = Bus("t075drill-probe", promote=False)
        return b._client if (b.online and b.probe()) else None
    except Exception:
        return None


_C = _control_client()
pytestmark = pytest.mark.skipif(
    _C is None,
    reason="live Redis required: runner_lock FAIL-OPENS offline, so an offline "
           "run would false-pass every pin (same gate as the RB-21 drills)")


def _lock_key(ns, agent):
    return f"{ns}:runner:{agent}"


def _presence_key(ns, agent):
    return f"{ns}:presence:{agent}"


def _cursor_key(ns, agent):
    return f"{ns}:cursor:{agent}"


def _spawn(agent, ns, home, mult, extra=()):
    """Launch the daemon as a real subprocess in an isolated drill namespace.
    HOME/USERPROFILE point at the drill dir so the stable-token dotfile
    (~/.akashic/daemon_<agent>.id) is sandboxed per test."""
    assert os.path.exists(DAEMON), \
        "M1-alpha build target scripts/bifrost_daemon.py does not exist yet (RED until built)"
    env = dict(os.environ)
    env.update({
        "BIFROST_NAMESPACE": ns,
        "_AISETUP_TEST_ISOLATED": "1",
        "AKASHIC_TIMEOUT_MULTIPLIER": mult,
        "HOME": home,
        "USERPROFILE": home,
        "PYTHONUNBUFFERED": "1",
    })
    return subprocess.Popen(
        [sys.executable, DAEMON, "--agent", agent, *extra],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=env, cwd=ROOT)


def _await_exit(proc, timeout=8):
    """Wait for the daemon's NATURAL exit (refusal / max-runtime paths); only a
    hang past `timeout` gets killed -- and the pin's assert then fails loudly.
    (Harness-defect fix, disclosed: the first cut terminated before waiting,
    which TerminateProcess'd refusal-path daemons mid-import into exit 1.)"""
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return proc.returncode, out or ""


def _kill(proc):
    """Cleanup for run-forever drills: terminate now, collect what it said."""
    if proc.poll() is None:
        proc.terminate()
    try:
        out, _ = proc.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return proc.returncode, out or ""


def _wait_for(fn, timeout, step=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None


def _cleanup_ns(ns):
    try:
        for k in _C.scan_iter(match=f"{ns}:*"):
            _C.delete(k)
    except Exception:
        pass


def _drill(tmp_path, tag):
    ns = f"t075drill-{os.getpid()}-{tag}"
    home = str(tmp_path)
    return ns, home


# --------------------------------------------------------------- M1-P1
def test_m1_p1_daemon_starts_holds_lock_registers_presence_and_survives(tmp_path):
    """M1-P1: starts, acquires lock, registers presence, survives '60s'.
    Scale: MULT=0.05 -> the pinned 60s of survival = 3.0s wall."""
    ns, home = _drill(tmp_path, "p1")
    agent = "t075a"
    proc = _spawn(agent, ns, home, "0.05")
    try:
        raw = _wait_for(lambda: _C.get(_lock_key(ns, agent)), timeout=12)
        assert raw, "P1: daemon never acquired the runner lock"
        rec = json.loads(raw)
        assert str(rec.get("token", "")).startswith("daemon:"), \
            "P1: lock token is the daemon's stable identity token"
        assert _wait_for(lambda: _C.get(_presence_key(ns, agent)), timeout=4), \
            "P1: daemon never registered presence (roster check)"
        card = json.loads(_C.get(_presence_key(ns, agent)))
        assert card.get("runtime_class") == "daemon", \
            "P1: presence card must be marked runtime_class=daemon (roster legibility)"
        time.sleep(3.0)  # the scaled 60 seconds
        assert proc.poll() is None, "P1: daemon died inside the survival window"
        assert _C.get(_lock_key(ns, agent)), "P1: lock lapsed while the daemon lived"
        assert not _C.exists(_cursor_key(ns, agent)), \
            "R-a2: the daemon must NEVER create its agent's cursor (no consume moves in wave 1)"
    finally:
        code, out = _kill(proc)
        _cleanup_ns(ns)


# --------------------------------------------------------------- M1-P2
def test_m1_p2_heartbeat_keeps_holder_fresh(tmp_path):
    """M1-P2: heartbeat keeps the lock TTL fresh; holder ts stays recent.
    Scale: MULT=0.2 -> hb=2s, ttl=12s; the pinned 'ts within last 10s'
    becomes 'ts advances across a 3.5s observation gap' at 1s stamp resolution."""
    ns, home = _drill(tmp_path, "p2")
    agent = "t075b"
    proc = _spawn(agent, ns, home, "0.2")
    try:
        raw = _wait_for(lambda: _C.get(_lock_key(ns, agent)), timeout=12)
        assert raw, "P2: daemon never acquired the lock"
        time.sleep(1.0)
        r1 = json.loads(_C.get(_lock_key(ns, agent)))
        time.sleep(3.5)
        r2 = json.loads(_C.get(_lock_key(ns, agent)) or "{}")
        assert r2, "P2: lock vanished mid-run (heartbeat not refreshing)"
        assert r2.get("token") == r1.get("token"), "P2: token must be stable across refreshes"
        assert int(r2.get("gen", -1)) == int(r1.get("gen", -2)), \
            "P2: a refresh must never mint a new generation (that is acquisition's job)"
        assert r2.get("ts") != r1.get("ts"), \
            "P2: holder ts did not advance across the refresh window -- heartbeat dead"
        ttl = _C.ttl(_lock_key(ns, agent))
        assert 0 < ttl <= 12, f"P2: lock TTL out of band ({ttl}s) -- refresh not re-arming expiry"
    finally:
        _kill(proc)
        _cleanup_ns(ns)


# --------------------------------------------------------------- M1-P11
def test_m1_p11_pre_existing_lock_refused_no_steal(tmp_path):
    """M1-P11: a pre-existing (foreign) lock means REFUSE AND EXIT CLEANLY --
    coexistence phase 1, the operator chooses who runs. No steal, no wait-loop."""
    ns, home = _drill(tmp_path, "p11")
    agent = "t075c"
    foreign = {"token": f"{agent}:999999:feedfacecafe", "pid": 999999,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "gen": 7}
    _C.set(_lock_key(ns, agent), json.dumps(foreign), ex=60)
    proc = _spawn(agent, ns, home, "0.1")
    try:
        code, out = _await_exit(proc, timeout=20)
        assert code == 0, f"P11: refusal must exit 0 (benign, operator-facing); got {code}\n{out}"
        assert "refused" in out.lower() and "no steal" in out.lower(), \
            f"P11: refusal provenance line missing from stdout:\n{out}"
        rec = json.loads(_C.get(_lock_key(ns, agent)))
        assert rec == foreign, "P11: the daemon touched a lock it refused (steal or clobber)"
    finally:
        _cleanup_ns(ns)


# --------------------------------------------------------------- M1-P12
def test_m1_p12_stable_token_reused_generation_increments(tmp_path):
    """M1-P12: daemon UUID lives in ~/.akashic/daemon_<agent>.id; a restart
    REUSES it; the fencing generation still increments per acquisition.
    Also pins the clean-exit contract: --max-runtime (raw seconds, drill hatch)
    ends the run benignly and RELEASES the lock."""
    ns, home = _drill(tmp_path, "p12")
    agent = "t075d"
    up_re = re.compile(r"\[daemon\] up .*token=(\S+) gen=(\d+)")

    def run_once():
        proc = _spawn(agent, ns, home, "0.1", extra=("--max-runtime", "2"))
        code, out = _await_exit(proc, timeout=25)
        m = up_re.search(out)
        assert m, f"P12: no '[daemon] up ... token= gen=' line in stdout:\n{out}"
        assert code == 0, f"P12: max-runtime exit must be benign 0; got {code}\n{out}"
        assert "clean exit" in out and "lock released" in out, \
            f"P12: clean-exit provenance missing:\n{out}"
        return m.group(1), int(m.group(2)), out

    tok1, gen1, _ = run_once()
    assert not _C.get(_lock_key(ns, agent)), "P12: lock must be RELEASED on clean exit"
    tok2, gen2, _ = run_once()
    try:
        assert tok1 == tok2, "P12: restart minted a NEW token -- the dotfile identity failed"
        assert gen2 > gen1, "P12: generation must increment per acquisition (L1b fencing)"
        dotfile = os.path.join(home, ".akashic", f"daemon_{agent}.id")
        assert os.path.exists(dotfile), "P12: ~/.akashic/daemon_<agent>.id missing"
        with open(dotfile, encoding="utf-8") as f:
            assert f.read().strip() == tok1, "P12: dotfile content is not the lock token"
        assert not _C.exists(_cursor_key(ns, agent)), \
            "R-a2: no cursor key, ever (consume path unmoved)"
    finally:
        _cleanup_ns(ns)


# --------------------------------------------------------------- R-a1 (flagged refinement)
def test_r_a1_same_token_twin_refused_first_daemon_unharmed(tmp_path):
    """R-a1: a second daemon on the SAME host (same dotfile -> same stable token)
    while the first lives must REFUSE -- runner_lock's own-token re-entrancy
    would otherwise let two processes both believe they hold the seat."""
    ns, home = _drill(tmp_path, "ra1")
    agent = "t075e"
    first = _spawn(agent, ns, home, "0.05")
    try:
        raw = _wait_for(lambda: _C.get(_lock_key(ns, agent)), timeout=12)
        assert raw, "R-a1: first daemon never came up"
        pid1 = json.loads(raw).get("pid")
        second = _spawn(agent, ns, home, "0.05")
        code, out = _await_exit(second, timeout=20)
        assert code == 0, f"R-a1: twin refusal must exit 0; got {code}\n{out}"
        assert "twin" in out.lower(), f"R-a1: twin teaching text missing:\n{out}"
        assert first.poll() is None, "R-a1: the LIVE daemon died when its twin knocked"
        rec = json.loads(_C.get(_lock_key(ns, agent)))
        assert rec.get("pid") == pid1, "R-a1: twin displaced the live holder's record"
    finally:
        _kill(first)
        _cleanup_ns(ns)
